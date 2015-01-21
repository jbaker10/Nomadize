## Nomadize

Move a local account or home folder to an NIH AD account. 

1) Mount the Nomadize.dmg

2) Open Terminal.app

3) From an account with Admin or Sudo rights run this command to start the wizard

`sudo /Volumes/Nomadize/Nomadize.py`

#### Follow the on screen instuctions:

Please choose the source account. If the account is not stored under /Users/ please move it to that path:

Please type in the new AD account:

#### Expected Output:

Deleting old local account

Creating new AD Mobile account

createmobileaccount built Jul 24 2014 20:00:42

You will see a few MCX errors, these are normal and can be ignored
MCXCCacheMCXRecordAndGraph(): vproc_swap_integer(NULL, VPROC_GSK_PERUSER_SUSPEND, &(uid=xxxxxxxxxx), NULL) failed

Setting ownership
