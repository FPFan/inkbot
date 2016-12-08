#!/usr/bin/python3

import time
import re
import warnings
import praw
import shelve
import traceback
from airtable.airtable import Airtable
from airtable import airtable

warnings.simplefilter('ignore')

# This is a class for inkbot find and respond with a link to an image of an ink
# On init, this class needs:
#     a Reddit User Name, Password, User Agent, and subreddit
#     an AirTable Key, Base, and Table
#     optionally a user can specify a lower limit to the number of comments and change
#     the wait time (in seconds) for exceptions.  The default is 2 minutes (60 seconds), 
#     however, the user may wish to increase this time
class InkBot:
    def __init__(self,
                 user_agent,
                 user_name,
                 user_pass,
                 client_id,
                 client_secret,
                 subreddit,
                 at_key,
                 at_base,
                 at_table,
                 limit=1000,
                 wait_time = 60,
                 debug=False ):

        self.debug = debug

        if self.debug:
            print("Setting up Inkbot....")

        self.user_agent    = user_agent
        self.user_name     = user_name
        self.user_pass     = user_pass
        self.client_id     = client_id
        self.client_secret = client_secret
        self.at_base       = at_base
        self.at_key        = at_key
        self.at_table      = at_table
        self.subreddit     = subreddit
        self.limit         = limit
        self.wait_time     = wait_time
        # DELETE ME--Old methodology, keep for now, delete line next update
        #self.r = praw.Reddit(user_agent = self.user_agent)


    # Start things up
    def start(self):
        if self.debug:
            print("Inkbot Logging into Reddit...")
        self.__login()

        if self.debug:
            print("Getting Inks from Airtable...")
        # Populate the Ink table from Airtable
        self.inklist = self.__get_inklist()

        if self.debug:
            print("Getting replied to posts from db...")
        # open up our comment database
        self.PostList = shelve.open('inkbot_list.db')

        if self.debug:
            print("Going into Main Loop...")
        self.__inkbot_loop()
     
    # Login to Reddit
    def __login(self):
        try:
            # DELETE ME--Old methodology, keep for now, delete line next update
            #self.r.login(username=self.user_name, password=self.user_pass, disable_warning=True)
            self.r = praw.Reddit(client_id = self.client_id,
                                 client_secret = self.client_secret,
                                 password = self.user_pass,
                                 user_agent = self.user_agent,
                                 username = self.user_name)
            if self.debug:
                print(self.r.user.me())
        except Exception as e:
            self.___handle_exception(e)

# Handle our exceptions.  This is the point where when things go bad we come.  What we are doing here is
# a bit of cleanup, and then we are sleeping the wait time passed in at init.  After that we are trying to
# restart things.   Hopefully this will happen until reddit is responsive again
    def ___handle_exception(self, e):
        if self.debug:
            traceback.print_exc()
            print("Inkbot had an Error: {}, going to try and continue".format(e))
        self.PostList.close()
        time.sleep(self.wait_time)
        self.start()
        exit()

# This is a function to get the inklist from Airtable, we do this once when we start up the script
# and with an update to the Airtable list, the bot will need to be restarted.
    def __get_inklist(self):
        #if self.debug:
        #    print("Airtable Login")
        at = airtable.Airtable(self.at_base, self.at_key)
        ink_list = []
        #if self.debug:
        #    print("Airtable get Table")
        at_inkbot = at.get(self.at_table)
        offset = at_inkbot.get('offset')
        ink_list.append(at_inkbot['records'])
        while offset:
            #if self.debug:
            #   print("Airtable get Offset loop")
            at_inkbot = at.get(self.at_table, offset=offset)
            offset = at_inkbot.get('offset')
            ink_list.append(at_inkbot['records'])
        return ink_list

# This is the function to reply to comments, comment out the comment.reply line to be able to test
# without posting to the subreddit, if self.debug == True, it will print to the command line the 
# output
    def __reply_to(self, comment, output, sid):
        # Debug prints, show up on the host running this bot
        if self.debug:
            print("\n---------------------------------------------")
            print("%s" %(output))
            print("\n---------------------------------------------")
        #comment.reply(output)
        self.PostList[sid] = 1
        self.PostList.sync()

# This is the action that is performed on a comment when it is detected.
    def __comment_action(self, c):
        regex = r"\[\[.*?\]\]"
        text = c.body
        output = ''
        comment_ID = c.id
        sid = str(c.id)
    
        # We will enter this if statement only if the [[ink name]] is found in the body of the post, else we just move on
        if re.search(regex, text):
           # Next we check to see if we have processed this comment in the past
           if sid not in self.PostList:
              # Now we create a list with all of the matches in the body of the comment
              matchList = re.findall(regex, text)
              found_match = 0 
              # At this point, we are ready to go over every match found and compare them to our inklist regex for commenting
              for match in matchList:
                  # Walk over the inklist, it is a list of lists, so we need two for loops
                  for atrecord in self.inklist:
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
                 retries = 20
                 while retries != 0:
                    try:
                       # Post comment to reddit and add this post ID to our responded to comment database
                       self.__reply_to(c, output, sid)
                       break  # exit the loop
                    except Exception as e:
                       if self.debug:
                           traceback.print_exc()
                           print("######Sleep Exception######")
                       time.sleep(self.wait_time)
                       retries -= 1
                       if retries == 0:
                           self.___handle_exception(e)

    def __inkbot_loop(self):
        try:
            # Start the comment stream for processesing
            for self.comment in praw.helpers.comment_stream(self.r, self.subreddit, limit=self.limit):
                self.__comment_action(self.comment)
        except (KeyboardInterrupt, SystemExit):
            if self.debug:
                print("\nKeyboard exit or System Exit, closing DB file\n")
            self.PostList.close()
            raise
        except Exception as e:
            self.___handle_exception(e)





