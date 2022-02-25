#!/usr/bin/python3

import sqlite3 as sl

if __name__ == "__main__":
    connection = sl.connect("reports.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM reports_table")
    results = cursor.fetchall()
    cursor.close()

    text = ""
    for i in range(len(results)):
        if (i != 0): text += '\n\n'
        
        row  = results[i]
        text += f"_id: {row[0]}\n" + f"reporter: {row[1]}\n" 
        text += f"reported_account: {row[2]}\n"
        text += f"original_msg_id: {row[3]}\n"
        text += f"mod_msg_id: {row[4]}\n" + f"thread_id: {row[5]}\n"
        text += f"msg_content: {row[6]}\n" + f"time: {row[7]}\n"
        text += f"resolution: {row[8]}\n"
    
    print(text)
