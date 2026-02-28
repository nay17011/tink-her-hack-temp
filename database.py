import sqlite3

def create_connection():
    conn = sqlite3.connect("attendance.db")
    return conn

def create_table():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        period TEXT,
        subject TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

create_table()