#!/usr/bin/python3

import sqlite3 as sl

if __name__ == "__main__":
    connection = sl.connect("reports.db")
    cursor = connection.cursor()
    cursor.execute("DROP TABLE reports_table")
    connection.commit()
    cursor.close()
    connection.close()