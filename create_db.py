import sqlite3

conn = sqlite3.connect("users.db")

cursor = conn.cursor()

# USERS TABLE

cursor.execute("""
CREATE TABLE users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE,

    password TEXT,

    email TEXT
)
""")

# PREDICTIONS TABLE

cursor.execute("""
CREATE TABLE predictions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT,

    role TEXT,

    city TEXT,

    experience INTEGER,

    work_type TEXT,

    salary REAL
)
""")

conn.commit()

conn.close()

print("✅ Database Created Successfully")