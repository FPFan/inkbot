#!/usr/bin/python3
#  Python 3 script for InkBot, public copy stripped of Identifying keys
import time
import praw
import re
import shelve
from airtable.airtable import Airtable
from airtable import airtable


# Set these variables to make run
user_agent = ("")

at_base = ('')
at_key = ('')
at_table = ('')
bot_user = ("")
bot_passwd = ("")
subreddit = ("")

# Start into Reddit, login, etc
r = praw.Reddit(user_agent = user_agent)
# You don't need to login if you are just reading, this is recommended to start
# Need to move this from r.login to OAuth in the future
#r.login(username=bot_user, password=bot_passwd, disable_warning=True)

# This is a function to get the inklist from Airtable, we do this once when we start up the script
# and with an update to the Airtable list, the bot will need to be restarted.
# This is a workaround since there is no way to get the entire table with the Airtable API, 
# so we get chunks at a time, makes some of the actions a little messier, clean up in the future
def get_inklist():
    at = airtable.Airtable(at_base, at_key)
    ink_list = []
    inkbot = at.get(at_table)
    offset = inkbot.get('offset')
    ink_list.append(inkbot['records'])
    while offset:
        inkbot = at.get(at_table, offset=offset)
        offset = inkbot.get('offset')
        ink_list.append(inkbot['records'])
    return ink_list

# This is the action that is performed on a comment when it is detected.
# comment-stream hands a comment to this function.
def inkbot_action(c):
    regex = r"\[\[.*?\]\]"
    text = c.body
    output = ''
    comment_ID = c.id
    sid = str(c.id)
    
    # We will enter this if statement only if the [[ink name]] is found in the body of the post, else we just move on
    if re.search(regex, text):
       # Next we check to see if we have processed this comment in the past
       if sid not in PostList:
          # Now we create a list with all of the matches in the body of the comment
          matchList = re.findall(regex, text)
          found_match = 0 
          # At this point, we are ready to go over every match found and compare them to our inklist regex for commenting
          for match in matchList:
              # Walk over the inklist, it is a list of lists, so we need two for loops
              for atrecord in inklist:
                  for ink in atrecord:
                      # Build up the regex, pulled from the Airtable
                      temp_reg='\[\[' + ink['fields']['Brand+ink regex'] + '\]\]'
                      # Build up the replacement string from Airtable
                      temp_replace='*  [' + ink['fields']['Name'] + '](' + ink['fields']['Imgur Address'] + ')   \n'
                      # will enter this if statement if the specific match from the comment matches this Airtable entry
                      if re.search(temp_reg, match, flags=re.IGNORECASE):
                          found_match = 1 
                          new_match= re.sub(temp_reg, temp_replace, match, 0, flags=re.IGNORECASE)
                          output = output + new_match
          # After processing all matches, and building up the output, post
          if found_match == 1:
             # retries for if reddit says we are posting too much, this gives us a 20min retry for posts
             # This will not be needed if your bot_user is an approved submitter for the sub-reddit
             # but it also doesn't hurt and catches other issues that may crop up
             retries = 20
             while retries != 0:
                try:
                   # Post comment to reddit and add this post ID to our responded to comment database
                   # uncomment c.reply to actually post using this code
                   #c.reply(output)

                   # Store this comment ID to our database
                   PostList[sid] = 1
                   PostList.sync()
                   break  # exit the loop
                except:
                   print("######Sleep Exception######")
                   # go to sleep for a minute before trying again
                   time.sleep(60)
                   retries -= 1
                   if retries == 0:
                       print("#######Failed to post#######")

             # Debug prints, show up on the host running this bot
             print("\n---------------------------------------------")
             print("%s" %(output))
             print("\n---------------------------------------------")


# Populate the table from Airtable
inklist = get_inklist()

# open up our comment database
PostList = shelve.open('inkbot_list.db')

# Start the comment stream for processesing
for c in praw.helpers.comment_stream(r, subreddit):
    inkbot_action(c)

PostList.close()


