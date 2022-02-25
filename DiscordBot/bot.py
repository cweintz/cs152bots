# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from report import State
import sqlite3 as sl # use DB to hold reports
import database as database

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'token.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    perspective_key = tokens['perspective']


class ModBot(discord.Client):
    def __init__(self, key):
        intents = discord.Intents.default()
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.perspective_key = key
        self.open_threads = dict()
        self.header = {"Authorization": f"Bot {discord_token}", "Content-Type": "application/json"}
        self.db = None
        self.open_entries = {}

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel

        # Open DB
        self.db = sl.connect("reports.db")
        if self.db is not None:
            try:
                cursor = self.db.cursor()
                cursor.execute(database.CREATE_REPORTS_DB)
                self.db.commit()
                cursor.close()
            except sl.Error as e: 
                print(e)
        else:
            print("An error has occured getting the database reference!")

        print("Bot is ready to go!")


    def send_thread_message(self, thread_id, message):
        requests.post(
            f"https://discord.com/api/v9/channels/{thread_id}/messages",
            json={"content": message}, headers=self.header
        )

    async def add_reactions(self, message, emojis):
        for emoji in emojis:
            await message.add_reaction(emoji)

    async def remove_reactions(self, message, emojis):
        for emoji in emojis:
            await message.remove_reaction(emoji, self.user)

    async def shift_forward(self, to_remove, to_add, message, next_message):
        await self.remove_reactions(message, to_remove)
        await self.add_reactions(message, to_add)
        self.send_thread_message(
            self.open_threads[message.id],
            next_message
        )

    async def on_raw_reaction_add(self, response):
        # get the latest reaction
        channel = await self.fetch_channel(response.channel_id)
        if channel.name != f"group-{self.group_num}-mod": return

        message = await channel.fetch_message(response.message_id)   
        if message.id not in self.open_threads: return
        
        selected = [reaction.emoji for reaction in message.reactions if reaction.count > 1]
        if len(selected) < 1: return

        
        if selected[0] == '❕':
            msg = self.open_entries[message.id].get_reported_history(self.db)
            await self.shift_forward(
                ['❕'],
                [],
                message,
                msg
            )
            return
        
        if selected[-1] == "👍":
            if self.open_entries[message.id].reporter == None:
                await self.shift_forward(
                    ['👍', '👎'], 
                    ["1️⃣", "2️⃣", "3️⃣", "4️⃣"],
                    message,
                    "What category best describes this message?\n" + 
                    "1️⃣: Threat of Danger or Harm\n" +
                    "2️⃣: Harassment\n" + "3️⃣: Spam\n" + 
                    "4️⃣: Suspicious Behavior\n"
                )
            else:
                await self.shift_forward(
                    ['👍', '👎'], 
                    ["🥾", "🔒", "👮", "🚮"],
                    message,
                    "Please react on the message with one of the following emojis to perform an" +
                    " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                    "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
                )
            return

        elif selected[-1] == "👎":
            await self.shift_forward(
                ['👍', '👎'],
                ["🤐", "🚮"],
                message, 
                "If you would like to restrict this user from reporting, please react on the" + 
                " message with 🤐. If you would like to discard this report, react with 🚮."
            )
            return

        if selected[-1] == "1️⃣":
            await self.shift_forward(
                ["1️⃣", "2️⃣", "3️⃣", "4️⃣"], 
                ['🔘', '🔴'],
                message, 
                "Please select a subcategory.\n" + "🔘: Credible Threat of Violence\n" + 
                "🔴: Suicidal Comments\n"
            )
            return

        if selected[-1] == "2️⃣":
            await self.shift_forward(
                ["1️⃣", "2️⃣", "3️⃣", "4️⃣"], 
                ['🟠', '🟡', '🟢'],
                message, 
                "Please select a subcategory.\n" + "🟠: Sexual Harassment\n" + 
                "🟡: Hate Speech\n" + "🟢: Bullying"
            )
            return
        
        if selected[-1] == "3️⃣":
            await self.shift_forward(
                ["1️⃣", "2️⃣", "3️⃣", "4️⃣"], 
                ['🔵', '🟣'],
                message, 
                "Please select a subcategory.\n" + "🔵: Unwanted Solicitation\n" + 
                "🟣: Scam or Fradulent Business"
            )
            return

        if selected[-1] == "4️⃣":
            await self.shift_forward(
                ["1️⃣", "2️⃣", "3️⃣", "4️⃣"], 
                ['⚫️', '⚪️', '🟤', '🔶'],
                message, 
                "Please select a subcategory.\n" + "⚫️: Possible Grooming\n" + 
                "⚪️: Impersonation or Compromised Account\n" + 
                "🟤: Attempt to Solicit Personal Information\n" +
                "🔶: Offer of Transportation"
            )
            return

        if selected[-1] == '🔘':
            await self.shift_forward(
                ['🔘', '🔴'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🔘', message.id)
            return

        if selected[-1] == '🔴':
            await self.shift_forward(
                ['🔘', '🔴'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🔴', message.id)
            return

        if selected[-1] == '🟠':
            await self.shift_forward(
                ['🟠', '🟡', '🟢',],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🟠', message.id)
            return

        if selected[-1] == '🟡':
            await self.shift_forward(
                ['🟠', '🟡', '🟢',],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🟡', message.id)
            return

        if selected[-1] == '🟢':
            await self.shift_forward(
                ['🟠', '🟡', '🟢'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🟢', message.id)
            return

        if selected[-1] == '🔵':
            await self.shift_forward(
                ['🔵', '🟣'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🔵', message.id)
            return

        if selected[-1] == '🟣':
            await self.shift_forward(
                ['🔵', '🟣'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🟣', message.id)
            return

        if selected[-1] == '⚫️':
            await self.shift_forward(
                ['⚫️', '⚪️', '🟤', '🔶'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '⚫️', message.id)
            return

        if selected[-1] == '⚪️':
            await self.shift_forward(
                ['⚫️', '⚪️', '🟤', '🔶'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '⚪️', message.id)
            return

        if selected[-1] == '🟤':
            await self.shift_forward(
                ['⚫️', '⚪️', '🟤', '🔶'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🟤', message.id)
            return

        if selected[-1] == '🔶':
            await self.shift_forward(
                ['⚫️', '⚪️', '🟤', '🔶'],
                ["🥾", "🔒", "👮", "🚮"],
                message,
                "Please react on the message with one of the following emojis to perform an" +
                " appropriate action.\n" + "Ban Account: 🥾\n" + "Restrict Account: 🔒\n" + 
                "Alert Law Enforcement: 👮\n" + "Do Nothing (Delete Report): 🚮"
            )
            database.update_categories(self.db, '🔶', message.id)
            return
        
        action = None
        if selected[-1] == "🥾":
            action = "USER BANNED"
            await self.remove_reactions(message, ["🥾", "🔒", "👮", "🚮"])
            self.send_thread_message(self.open_threads[message.id], "User has been banned.")

        elif selected[-1] == "🔒":
            action = "USER RESTRICTED (MESSAGING)"
            await self.remove_reactions(message, ["🥾", "🔒", "👮", "🚮"])
            self.send_thread_message(self.open_threads[message.id], "User has been restricted.")

        elif selected[-1] == "👮":
            action = "AUTHORITIES ALERTED"
            await self.remove_reactions(message, ["🥾", "🔒", "👮", "🚮"])
            self.send_thread_message(self.open_threads[message.id], "Local authorities are being notified.")

        elif selected[-1] == "🚮":
            action = "REPORT DELETED (NO ACTION)"
            await self.remove_reactions(message, ["🥾", "🔒", "👮", "🚮"])
            self.send_thread_message(self.open_threads[message.id], "Message is being deleted.")

        elif selected[-1] == "🤐":
            action = "USER RESTRICTED (REPORTING)"
            await self.remove_reactions(message, ["🥾", "🔒", "👮", "🚮"])
            self.send_thread_message(self.open_threads[message.id], "User has been restricted from reporting.")
        
        # remove thread from list in bot and delete message. this does NOT delete the thread
        database.update_resolution(self.db, action, message.id)
        del self.open_threads[message.id]
        await message.delete()


    async def handle_mod_message(self, message):
        header = {"Authorization": f"Bot {discord_token}", "Content-Type": "application/json"}
        data = {"name": f"{message.id}", "auto_archive_duration": 60}
        response = json.loads(requests.post(
            f"https://discord.com/api/v9/channels/{message.channel.id}/messages/{message.id}/threads", 
            json=data, headers=header
        ).content)

        thread_id = response["id"]
        response = json.loads(requests.post(
            f"https://discord.com/api/v9/channels/{thread_id}/messages",
            json={"content": "sample information..."}, headers=header
        ).content)

        response = json.loads(requests.post(
            f"https://discord.com/api/v9/channels/{thread_id}/messages",
            json={"content": "Is this a valid report? Please react on the outer message with 👍 or 👎.\n" +
            "You can view the report history with ❕."}, headers=header
        ).content)

        await self.add_reactions(message, ['👍', '👎'])
        self.open_threads[message.id] = thread_id

        db_entry = database.Entry()
        db_entry.fill_information(message, thread_id)
        db_entry.submit_entry(self.db)
        self.open_entries[message.id] = db_entry
        to_add = ['❕'] 
        await self.add_reactions(message, to_add)


    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        is_mod_message = (
            not isinstance(message.channel, discord.channel.DMChannel) and message.channel.name == f"group-{self.group_num}-mod" 
        )

        # Ignore messages from the bot 
        if (message.author.id == self.user.id) and (not is_mod_message):
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            if (is_mod_message):
                await self.handle_mod_message(message)
            else: await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        report = self.reports[author_id]

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await report.handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # # If the report is complete or cancelled, remove it from our map
        if report.report_complete():
            # get mod channel
            mod_channel = [v for v in self.mod_channels.values() 
                if v.name == f"group-{self.group_num}-mod"
            ][0].id
            mod_channel = await self.fetch_channel(mod_channel)
             
            msg_channel = await self.fetch_channel(report.msg_channel_id)
            message = await msg_channel.fetch_message(report.reported_msg)

            # get scores and send to mod channel
            scores = self.eval_text(message) 
            await mod_channel.send(
                self.code_format(
                    json.dumps(scores, indent=2), 
                    message, "manually", author_id, report.category, report.subcategory, report.additional_info
                )
            )

        if report.report_complete() or report.state == State.REPORT_CANCEL:
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')

        mod_channel = self.mod_channels[message.guild.id]
        scores = self.eval_text(message)

        if len([val for val in scores.values() if val > .75]) > 0:
            await mod_channel.send(self.code_format(json.dumps(scores, indent=2), message, "automatically"))

    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores

    def code_format(self, text, message, method, author_id=None, category=None, subcategory=None, additional_info=None):
        if method == "manually": 
            toReturn = f"```This message was flagged {method} by user {author_id}\n\n{message.author.name}: \"{message.content}\"\n\n"
        else:                                          
            toReturn = f"```This message was flagged {method}\n\n{message.author.name}: \"{message.content}\"\n\n"
        toReturn += f"Message ID: {message.id} Author ID: {message.author.id}\n\n"
        
        if category != None:
            toReturn += f"Category: {category} Subcategory: {subcategory}\n\n"

        if additional_info != None: 
            toReturn += f"Additional Info: {additional_info}\n\n"

        toReturn += text + "```"
        return toReturn


client = ModBot(perspective_key)
client.run(discord_token)
