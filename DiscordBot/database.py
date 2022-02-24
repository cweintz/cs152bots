CREATE_REPORTS_DB = """CREATE TABLE IF NOT EXISTS reports_table (
                            _id INTEGER PRIMARY KEY AUTOINCREMENT,
                            reporter INTEGER,
                            reported_account INTEGER NOT NULL,
                            original_msg_id INTEGER NOT NULL,
                            mod_msg_id INTEGER NOT NULL,
                            msg_content TEXT NOT NULL,
                            time TIMESTAMP NOT NULL, 
                            resolution TEXT NOT NULL
                       );"""

ADD_MANUAL_REPORT = """INSERT INTO reports_table(
                         reporter, reported_account, original_msg_id,
                         mod_msg_id, msg_content, time, resolution
                       ) VALUES (?, ?, ?, ?, ?, ?, ?)"""

ADD_AUTOMATIC_REPORT = """INSERT INTO reports_table(
                              reported_account, original_msg_id,
                              mod_msg_id, msg_content, time, resolution
                          ) VALUES (?, ?, ?, ?, ?, ?)"""


class Entry():
     def __init__(self):
          self.reporter = None
          self.reported_acc = None
          self.original_msg_id = None
          self.mod_msg_id = None
          self.time = None
          self.resolution = None
