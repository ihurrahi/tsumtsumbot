# tsumtsumbot
Auto heart sender for the Disney TsumTsum game. Written in Python, designed to run over BlueStacks on Windows.

It works by taking a screenshot of the BlueStacks window, looking for pre-defined pictures, and decides what to click on next.

1. Start by clicking the "Start button"
1. Close any announcements (and also click the "Do not show" checkbox)
1. Claim hearts individually from mailbox
1. Send hearts to each person on the leaderboard
1. Occasionally claim more hearts individually from mailbox
1. Stop and close the app once an inactive player is detected (someone with a 0 score)

Notes:
* It takes over your mouse so you won't be able to use your computer when it's running.
* Images are in the media folder.
* Occasionally, I found that I randomly hit an error (network or random in-game errors) that messes things up, so each time I click on something, I also check for this error message.
* Also supported is sending how many hearts were claimed over IFTTT (which I routed to a spreadsheet to keep track of heart sending and to notifications on my phone so I knew if heart sending had stopped).
