import sqlite3
from flask import Flask

app = Flask(__name__)
DATABASE = 'data.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        probe_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        mac_address TEXT NOT NULL,
        ports TEXT NOT NULL,
        scan_date TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS online (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        probe_id INTEGER NOT NULL,
        ping_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """)
    conn.commit()
    conn.close()

# Initialize the database before the first request
with app.app_context():
    init_db()
