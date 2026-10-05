import os
import sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'attendance.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as file:
        conn.executescript(file.read())

    admin = conn.execute('SELECT id FROM users WHERE username = ?', ('admin',)).fetchone()
    if admin is None:
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123')),
        )

    conn.commit()
    conn.close()


def fetch_employee_by_code(code):
    conn = get_connection()
    employee = conn.execute('SELECT * FROM students WHERE employee_code = ? LIMIT 1', (code,)).fetchone()
    conn.close()
    return employee


def fetch_user_by_username(username):
    conn = get_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? LIMIT 1', (username,)).fetchone()
    conn.close()
    return user
