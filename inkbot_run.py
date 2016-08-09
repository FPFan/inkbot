#!/usr/bin/python3

from inkbot import InkBot


user_agent = ("<User Agent Here>")
at_base = ('<AirTable Base Here>')
at_key = ('<AirTable Key Here>')
at_table = ('<AirTable Table ID here>')
bot_user = ("<User Name Here>")
bot_passwd = ("<User Passwd Here>")
subreddit = ("<Subreddit Here>")

myinkbot = InkBot( user_agent = user_agent,
                      user_name  = bot_user,
                      user_pass  = bot_passwd,
                      at_key     = at_key,
                      at_base    = at_base,
                      at_table   = at_table,
                      subreddit  = subreddit,
                      debug=True )

myinkbot.start()
