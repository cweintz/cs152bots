from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    REPORT_CANCEL = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_REASON = auto()
    AWAITING_THREAT = auto()
    AWAITING_SUICIDAL = auto()
    AWAITING_HARASSMENT = auto()
    AWAITING_SPAM = auto()
    AWAITING_SUSPICIOUS = auto()
    AWAITING_AUTHORITIES = auto()
    AWAITING_BLOCK = auto()
    AWAITING_INFO = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    BLOCK_REQUEST = "Would you like to block this user from sending you more messages? (yes/no)"
    INFO_REQUEST = "If you would like to provide additional information, please reply to this message with the additional information that you would like to provide (all in one message). Otherwise, reply 'no'."

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.reported_acc = None
        self.reported_msg = None
        self.msg_content = None
        self.msg_channel_id = None
        self.category = None
        self.subcategory = None
        self.additional_info = None

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_CANCEL
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message
            self.msg_content = message.content
            self.msg_channel_id = message.channel.id
            self.reported_msg = message.id
            self.reported_acc = message.author.id
            reply = "I found this message:\n" + "```" + message.author.name + ": " + message.content + "``` \n"
            reply += "What is your reason for reporting this message? "
            reply += "Reply '1' for Threat of Danger/Harm, "
            reply += "'2' for Harassment, "
            reply += "'3' for Spam, or "
            reply += "'4' for Suspicious behavior."
            self.state = State.AWAITING_REASON
            return [reply]

        if self.state == State.AWAITING_REASON:
            m = message.content
            reply = "I don't understand that response. Please reply with either '1', '2', '3', or '4'."
            if m == "1":
                self.category = "Threat of Danger/Harm"
                reply = "You selected 'Threat of Danger/Harm'. "
                reply += "How would you categorize the threat of danger/harm? "
                reply += "Reply '1' for Credible Threat of Violence or '2' for Suicidal Comments."
                self.state = State.AWAITING_THREAT
            elif m == "2":
                self.category = "Harassment"
                reply = "You selected 'Harassment'. "
                reply += "How would you categorize the harassment? "
                reply += "Reply '1' for Sexual Harassment, '2' for Hate Speech, or '3' for Bullying."
                self.state = State.AWAITING_HARASSMENT
            elif m == "3":
                self.category = "Spam"
                reply = "You selected 'Spam'. "
                reply += "How would you categorize the spam? "
                reply += "Reply '1' for Unwanted Solicitation or '2' for Scam/Fraudulent Business."
                self.state = State.AWAITING_SPAM
            elif m == "4":
                self.category = "Suspicious Behavior"
                reply = "You selected 'Suspicious Behavior'. "
                reply += "How would you categorize the suspicious behavior? "
                reply += "Reply '1' for Possible Grooming, '2' for Impersonation/Compromised Account, '3' for Attempting to Solicit Personal Information, or '4' for Offer of Transportation."
                self.state = State.AWAITING_SUSPICIOUS
            return [reply]

        if self.state == State.AWAITING_THREAT:
            m = message.content
            reply = "I don't understand that response. Please reply with either '1' or '2'."
            if m == "1":
                self.subcategory = "Credible Threat of Violence"
                reply = "You selected 'Credible Threat of Violence'. "
                reply += "If you feel that the threat is imminent, consider calling 911."
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "2":
                self.subcategory = "Suicidal Comments"
                reply = "You selected 'Suicidal Comments'. "
                reply += "Would you would like us to send this account an anonymous message with suicide prevention resources? (yes/no)"
                self.state = State.AWAITING_SUICIDAL
            return [reply]

        if self.state == State.AWAITING_HARASSMENT:
            m = message.content
            reply = "I don't understand that response. Please reply with either '1', '2', or '3'."
            if m == "1":
                self.subcategory = "Sexual Harassment"
                reply = "You selected 'Sexual Harassment'. "
                reply += "We will investigate this report and potentially ban this user. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "2":
                self.subcategory = "Hate Speech"
                reply = "You selected 'Hate Speech'. "
                reply += "We will investigate this report and potentially ban this user. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "3":
                self.subcategory = "Bullying"
                reply = "You selected 'Bullying'. "
                reply += "We will investigate this report and potentially ban this user. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_SPAM:
            m = message.content
            reply = "I don't understand that response. Please reply with either '1' or '2'."
            if m == "1":
                self.subcategory = "Unwanted Solicitation"
                reply = "You selected 'Unwanted Solicitation'. "
                reply += "We will investigate this report and potentially ban this user. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "2":
                self.subcategory = "Scam/Fraudulent Business"
                reply = "You selected 'Scam/Fraudulent Business'. "
                reply += "We will investigate this report and potentially ban this user. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_SUSPICIOUS:
            m = message.content
            reply = "I don't understand that response. Please reply with either '1', '2', '3', or '4'."
            if m == "1":
                self.subcategory = "Possible Grooming"
                reply = "You selected 'Possible Grooming'. "
                reply += "Is this a serious matter that may potentially involve the authorities? (yes/no)"
                self.state = State.AWAITING_AUTHORITIES
            elif m == "2":
                self.subcategory = "Impersonation/Compromised Account"
                reply = "You selected 'Impersonation/Compromised Account'. "
                reply += "We will investigate the suspicious behavior and take action if necessary. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "3":
                self.subcategory = "Attempting to Solicit Personal Information"
                reply = "You selected 'Attempting to Solicit Personal Information'. "
                reply += "Is this a serious matter that may potentially involve the authorities? (yes/no)"
                self.state = State.AWAITING_AUTHORITIES
            elif m == "4":
                self.subcategory = "Offer of Transportation"
                reply = "You selected 'Offer of Transportation'. "
                reply += "Is this a serious matter that may potentially involve the authorities? (yes/no)"
                self.state = State.AWAITING_AUTHORITIES
            return [reply]

        if self.state == State.AWAITING_AUTHORITIES:
            m = message.content
            reply = "I don't understand that response. Please reply with either 'yes' or 'no'."
            if m == "yes":
                reply = "A member of our team will investigate the suspicious behavior and alert authorities if necessary. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "no":
                reply = "We will investigate the suspicious behavior and take action if necessary."
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_SUICIDAL:
            m = message.content
            reply = "I don't understand that response. Please reply with either 'yes' or 'no'."
            if m == "yes":
                user = await self.client.fetch_user(self.reported_acc)
                await user.send(self.SUICIDE_PREVENTION_MESSAGE)
                reply = "The message has been sent, and resources have been shared anonymously with the user in concern. "
                reply += self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            elif m == "no":
                reply = self.BLOCK_REQUEST
                self.state = State.AWAITING_BLOCK
            return [reply]

        if self.state == State.AWAITING_BLOCK:
            m = message.content
            reply = "I don't understand that response. Please reply with either 'yes' or 'no'."
            if m == "yes":
                reply = "The user has been blocked. "
                reply += self.INFO_REQUEST
                self.state = State.AWAITING_INFO
            elif m == "no":
                reply = self.INFO_REQUEST
                self.state = State.AWAITING_INFO
            return [reply]

        if self.state == State.AWAITING_INFO:
            m = message.content
            reply = "Thank you for your report."
            if m != "no":
                self.additional_info = m
                reply = "We've attached the additional information you've provided to your report. " + reply
            self.state = State.REPORT_COMPLETE
            return [reply]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    