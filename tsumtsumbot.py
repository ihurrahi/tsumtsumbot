import ctypes
from ctypes.wintypes import RECT
import cv2
import datetime
import logging
import numpy as np
import os
from PIL import ImageGrab
import signal
import sys
import time
import requests
import json

BASE = 'C:\\Users\\andyl\\Desktop\\tsumtsumbot\\'
MEDIA_BASE = os.path.join(BASE, 'media')

APP_TITLE_OFFSET = 60
HEART_COLLECT_OFFSET_X = 160
HEART_COLLECT_OFFSET_Y = -10
DO_NOT_SHOW_OFFSET = -58
SCROLL_AMOUNT = 1

logging.basicConfig(filename=os.path.join(BASE, 'log'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

offsetx = offsety = 0
app_center = (0, 0)
bluestacks = None

def load_config():
  path = os.path.join(BASE, 'config')
  if os.path.exists(path):
    with open(path, 'r') as f:
      return json.loads(f.read().strip())
  return None

def find_window_handle(name):
  windows = {}
  def process_window(hwnd, lParam):
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    windows[buff.value] = hwnd
    return True
  proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
  ctypes.windll.user32.EnumWindows(proc(process_window), 0)
  emulator = None
  for window_name, handle in windows.iteritems():
    if name in window_name:
      return handle

def take_current_ss():
  global global_offsetx, global_offsety, app_center, bluestacks

  fname = os.path.join(MEDIA_BASE, 'current.jpg')
  rect = RECT()
  ctypes.windll.user32.GetWindowRect(bluestacks, ctypes.byref(rect))
  global_offsetx = rect.left
  global_offsety = rect.top
  app_center = ((rect.left + rect.right) / 2, (rect.top + rect.bottom) / 2)
  ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(fname, 'jpeg')
  return fname

def click(x, y):
  ctypes.windll.user32.SetCursorPos(x, y)
  time.sleep(0.1)
  ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # left down
  time.sleep(0.1)
  ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # left up
  time.sleep(0.1)

def scroll(x, y, scroll_amount):
  ctypes.windll.user32.SetCursorPos(x, y)
  time.sleep(0.1)
  ctypes.windll.user32.mouse_event(2048, 0, 0, scroll_amount, 0)
  time.sleep(0.1)

def find_image_center(image_path, screen_path):
  target, current = cv2.imread(image_path), cv2.imread(screen_path)
  result = cv2.matchTemplate(target, current, cv2.TM_CCOEFF_NORMED)
  threshold = 0.8
  l = np.where(result >= threshold)
  if len(l[0]) > 0:
    x, y = int(l[1][0]), int(l[0][0])
    targety, targetx = target.shape[:2]
    return x + (targetx / 2), y + (targety / 2)
  else:
    return -1, -1

class Target():
  def __init__(self, name, offsetx=0, offsety=0):
    self.name = name
    self.offsetx = offsetx
    self.offsety = offsety

def click_image(targets):
  targets = [Target('error.jpg')] + targets
  screen_path = take_current_ss()
  for i, target in enumerate(targets):
    logger.debug('Trying to click %s' % target.name)
    s = time.time()
    x, y = find_image_center(os.path.join(MEDIA_BASE, target.name), screen_path)
    if x != -1 and y != -1:
      click(x + global_offsetx + target.offsetx, y + global_offsety + target.offsety)
      if i == 0:
        logger.debug('...Clicked on error message. Sleeping for a bit first')
        time.sleep(4)
        continue
      logger.debug('...Clicked %s' % target.name)
      time.sleep(0.5)
      return True
    logger.debug('...Could not find %s' % target.name)
  return False

def wait_for(targets, timeout=0.1):
  start = time.time()
  while time.time() - start < timeout:
    screen_path = take_current_ss()
    for target in targets:
      waitx, waity = find_image_center(os.path.join(MEDIA_BASE, target.name), screen_path)
      if waitx != -1 and waity != -1:
        logger.debug('...Found %s' % target.name)
        return True
    time.sleep(0.5)
  logger.debug('...Timed out looking for %s' % ','.join(map(lambda t: t.name, targets)))
  return False

def claim_individual_hearts():
  hearts_received = 0
  click_image([Target('messages_button.jpg')])
  wait_for([Target('close_button.jpg')], timeout=10)
  time.sleep(1)
  found = click_image([Target('heart_gift.jpg', offsetx=HEART_COLLECT_OFFSET_X, offsety=HEART_COLLECT_OFFSET_Y)])
  while found:
    wait_for([Target('heart_gift_ok.jpg'), Target('heart_gift_ok2.jpg')], timeout=10)
    receive_gift_ok = click_image([Target('heart_gift_ok.jpg'), Target('heart_gift_ok2.jpg')])
    wait_for([Target('received.jpg'), Target('sent.jpg')], timeout=10)
    received = click_image([Target('received.jpg'), Target('sent.jpg')])
    wait_for([Target('close_button.jpg')], timeout=10)
    if receive_gift_ok and received:
      hearts_received += 1
    found = click_image([Target('heart_gift.jpg', offsetx=HEART_COLLECT_OFFSET_X, offsety=HEART_COLLECT_OFFSET_Y)])
  click_image([Target('close_button.jpg')])
  return hearts_received

def main():
  config = load_config() or {}
  hearts_received = 0
  hearts_given = 0
  start = time.time()
  global bluestacks
  bluestacks = find_window_handle('BlueStacks App Player')

  def signal_handler(signal, frame):
    end = time.time()
    logger.info('Finished, took %ds' % (end - start))
    if hearts_received > 0 or hearts_given > 0:
      if config.get('secret_key'):
        url = 'https://maker.ifttt.com/trigger/tsumtsumbot/with/key/%s' % config.get('secret_key')
        data = {'value1': hearts_received, 'value2': hearts_given}
        requests.post(url, data=data)
    sys.exit(0)
  signal.signal(signal.SIGINT, signal_handler)
  
  new_app = click_image([Target('tsumtsumicon.jpg')])
  if new_app:
    timeout = 200
    time.sleep(4)
    start_time = time.time()
    start_button = False
    while not start_button and time.time() - start_time < timeout:
      click(app_center[0], app_center[1])
      start_button = wait_for([Target('start_button.jpg')])
    if time.time() - start_time >= timeout:
      logger.info('Could not start up app, quitting early')
      return

  click_image([Target('start_button.jpg')])
  wait_for([Target('do_not_show.jpg')], timeout=15)
  announcements = click_image([Target('do_not_show.jpg', offsetx=DO_NOT_SHOW_OFFSET)])
  while announcements:
    click_image([Target('close_button.jpg')])
    time.sleep(4)
    announcements = click_image([Target('do_not_show.jpg', offsetx=DO_NOT_SHOW_OFFSET)])
  
  hearts_received += claim_individual_hearts()
  hearts_received += claim_individual_hearts() 

  # Sroll to the top
  found = False
  while not found:
    for _ in xrange(5):
      scroll(app_center[0], app_center[1], 1)
    found = wait_for([Target('rank1.jpg')])

  # Click on all the hearts
  found_inactive_players = wait_for([Target('inactve_player.jpg')])
  attempts = 0
  while not found_inactive_players:
    attempts += 1
    if attempts % 30 == 0:
      hearts_received += claim_individual_hearts()
    found = click_image([Target('heart_gift_send.jpg')])
    while found:
      time.sleep(0.5)
      wait_for([Target('heart_gift_ok.jpg')], timeout=10)
      receive_gift_ok = click_image([Target('heart_gift_ok.jpg')])
      wait_for([Target('sent.jpg')], timeout=10)
      sent = click_image([Target('sent.jpg')])
      wait_for([Target('messages_button.jpg')], timeout=10)
      if receive_gift_ok and sent:
        hearts_given += 1
      found = click_image([Target('heart_gift_send.jpg')])
    # Scroll down a bit, approximately one page
    for _ in xrange(SCROLL_AMOUNT):
      scroll(app_center[0], app_center[1], -1)
    found_inactive_players = wait_for([Target('inactve_player.jpg')])
    
    # Safeguard
    if attempts > 400:
      logger.info('Something went wrong - trying to give too many hearts')
      break

  logger.info(datetime.datetime.utcnow().isoformat())
  logger.info('Hearts received: %d' % hearts_received)
  logger.info('Hearts given: %d' % hearts_given)

  click_image([Target('app_title.jpg', offsetx=APP_TITLE_OFFSET)])

  signal_handler(None, None)
  
def current_mouse_pos():
  class Point(ctypes.Structure):
    _fields_ = [('x', ctypes.c_ulong), ('y', ctypes.c_ulong)]
  p = Point()
  ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
  return p.x, p.y

if __name__ == '__main__':
  main()