import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'shop.db'

def create_admin():
    username = 'is_admin'
    password = '1'  # Thay đổi mật khẩu này thành mật khẩu mong muốn
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", (username, hashed_password, 1))
        conn.commit()
        print("Admin user created successfully.")
    except sqlite3.IntegrityError:
        print("Username already exists.")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin()
