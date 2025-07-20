import sqlite3
import os
import hashlib


class Database:
    def __init__(self, db_path="sqlite.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Создаем таблицу администраторов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Создаем таблицу постов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                image TEXT,
                content TEXT NOT NULL
            )
        ''')

        # Проверяем наличие администратора по умолчанию
        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            hashed_pw = hashlib.sha256('password'.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO admin (id, name, password) VALUES (?, ?, ?)",
                (1, 'admin', hashed_pw)
            )

        conn.commit()
        conn.close()

    def authenticate(self, name: str, password: str) -> bool:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM admin WHERE name = ? AND password = ?",
            (name, hashed_pw)
        )
        result = cursor.fetchone()[0] > 0
        conn.close()
        return result

    def insert_post(self, post_id: int, title: str, content: str, image: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO posts (id, title, content, image) VALUES (?, ?, ?, ?)",
            (post_id, title, content, image)
        )
        conn.commit()
        conn.close()

    def insert_admin(self, user_id: int, name: str, password: str):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admin (id, name, password) VALUES (?, ?, ?)",
                (user_id, name, hashed_pw)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Если администратор с таким ID уже существует
            raise ValueError(f"Admin with ID {user_id} already exists")
        finally:
            conn.close()
    def get_all_posts(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, image, content FROM posts ORDER BY id DESC")
        posts = cursor.fetchall()
        conn.close()
        return [dict(post) for post in posts]

    def get_max_post_id(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM posts")
        max_id = cursor.fetchone()[0]
        conn.close()
        return max_id if max_id else 0

    def get_post(self, post_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, image, content FROM posts WHERE id = ?",
            (post_id,)
        )
        post = cursor.fetchone()
        conn.close()
        return dict(post) if post else None

    def update_post(self, post_id: int, title: str, content: str, image: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE posts SET title = ?, content = ?, image = ? WHERE id = ?",
            (title, content, image, post_id)
        )
        conn.commit()
        conn.close()

    def delete_post(self, post_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()

    def get_admin(self, admin_id=1):
        """Получить данные администратора"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, password FROM admin WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        conn.close()
        return dict(admin) if admin else None

    def update_admin(self, admin_id, name, password):
        """Обновить данные администратора"""
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE admin SET name = ?, password = ? WHERE id = ?",
            (name, hashed_pw, admin_id)
        )
        conn.commit()
        conn.close()