import re
import datetime

CREATE_REPORTS_DB = """CREATE TABLE IF NOT EXISTS reports_table (
                            _id INTEGER PRIMARY KEY,
                            reporter INTEGER,
                            reported_account INTEGER NOT NULL,
                            original_msg_id INTEGER NOT NULL,
                            mod_msg_id INTEGER NOT NULL,
                            thread_id INTEGER NOT NULL,
                            msg_content TEXT NOT NULL,
                            time TIMESTAMP NOT NULL, 
                            resolution TEXT
                       );"""

ADD_MANUAL_REPORT = """INSERT INTO reports_table(
                         reporter, reported_account, original_msg_id,
                         mod_msg_id, thread_id, msg_content, time
                       ) VALUES (?, ?, ?, ?, ?, ?, ?);"""

ADD_AUTOMATIC_REPORT = """INSERT INTO reports_table(
                              reported_account, original_msg_id,
                              mod_msg_id, thread_id, msg_content, time
                          ) VALUES (?, ?, ?, ?, ?, ?);"""

ADD_RESOLUTION = """UPDATE reports_table SET resolution = ? WHERE mod_msg_id = ?"""


class Entry():
     def __init__(self):
          self.reporter = None
          self.reported_acc = None
          self.original_msg_id = None
          self.mod_msg_id = None
          self.time = None
          self.resolution = None
          self.msg_content = None
          self.thread_id = None

     def fill_information(self, message, thread_id):
          lines = [line.strip() for line in message.content.splitlines() if line][:3]
          
          # get reporter (if manually reported)
          reporter = re.fullmatch(
               "```This message was flagged manually by user ([0-9]+)",
               lines[0]
          )
          if reporter != None:
               self.reporter = int(reporter.group(1))

          # get reported acc id and message id
          reported_msg_info = re.fullmatch(
               "Message ID: ([0-9]+) Author ID: ([0-9]+)",
               lines[2]
          )
          self.original_msg_id = int(reported_msg_info.group(1))
          self.reported_acc = int(reported_msg_info.group(2))

          # set the rest of the info
          self.msg_content = lines[1].split(": ")[1]
          self.time = datetime.datetime.now()
          self.mod_msg_id = message.id
          self.thread_id = thread_id

     def submit_entry(self, db):
          cursor = db.cursor()
          
          if self.reporter == None:
               cursor.execute(
                    ADD_AUTOMATIC_REPORT,
                    (self.reported_acc, self.original_msg_id, self.mod_msg_id,
                    self.thread_id, self.msg_content, self.time)
               )
          else:
               cursor.execute(
                    ADD_MANUAL_REPORT,
                    (self.reporter, self.reported_acc, self.original_msg_id,
                    self.mod_msg_id, self.thread_id, self.msg_content, self.time)
               )
          
          db.commit()
          cursor.close()

def update_resolution(db, action, mod_msg_id):
     cursor = db.cursor()
     cursor.execute(ADD_RESOLUTION, (action, mod_msg_id))
     db.commit()
     cursor.close()