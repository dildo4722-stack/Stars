import sqlite3
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

DB_PATH = "database.db"

def init_db():
    """Инициализация базы данных"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date TEXT,
                balance_rub REAL DEFAULT 0,
                balance_stars INTEGER DEFAULT 0,
                balance_ton REAL DEFAULT 0,
                balance_usd REAL DEFAULT 0
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount_rub REAL,
                amount_stars INTEGER,
                amount_ton REAL,
                amount_usd REAL,
                status TEXT,
                created_at TEXT,
                admin_id INTEGER,
                comment TEXT
            )
        ''')
        
        # Таблица заявок на покупку звезд
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars_amount INTEGER,
                currency TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                processed_at TEXT
            )
        ''')
        
        # Таблица для хранения баланса звезд бота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_stars_balance (
                id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        ''')
        
        # Инициализируем баланс бота, если его нет
        cursor.execute('SELECT * FROM bot_stars_balance')
        if not cursor.fetchone():
            cursor.execute('INSERT INTO bot_stars_balance (balance) VALUES (0)')
        
        conn.commit()

async def register_user(user_id: int, username: str, first_name: str, last_name: str = None):
    """Регистрация нового пользователя"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, registration_date, balance_rub, balance_stars, balance_ton, balance_usd)
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0)
        ''', (user_id, username, first_name, last_name, now))
        
        conn.commit()
        return cursor.rowcount > 0

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение данных пользователя"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

async def update_balance(user_id: int, rub: float = 0, stars: int = 0, ton: float = 0, usd: float = 0):
    """Обновление баланса пользователя"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        if rub != 0:
            cursor.execute('UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?', (rub, user_id))
        if stars != 0:
            cursor.execute('UPDATE users SET balance_stars = balance_stars + ? WHERE user_id = ?', (stars, user_id))
        if ton != 0:
            cursor.execute('UPDATE users SET balance_ton = balance_ton + ? WHERE user_id = ?', (ton, user_id))
        if usd != 0:
            cursor.execute('UPDATE users SET balance_usd = balance_usd + ? WHERE user_id = ?', (usd, user_id))
        
        conn.commit()

async def get_balance(user_id: int, currency: str = 'rub') -> float:
    """Получение баланса в определенной валюте"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT balance_{currency} FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

async def add_transaction(user_id: int, type: str, amount_rub: float = 0, amount_stars: int = 0, 
                          amount_ton: float = 0, amount_usd: float = 0, status: str = 'completed',
                          admin_id: int = None, comment: str = None):
    """Добавление записи о транзакции"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO transactions 
            (user_id, type, amount_rub, amount_stars, amount_ton, amount_usd, status, created_at, admin_id, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, type, amount_rub, amount_stars, amount_ton, amount_usd, status, now, admin_id, comment))
        
        conn.commit()

async def create_purchase_request(user_id: int, stars_amount: int, currency: str, amount: float) -> int:
    """Создание заявки на покупку звезд"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO purchase_requests (user_id, stars_amount, currency, amount, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, stars_amount, currency, amount, now))
        
        conn.commit()
        return cursor.lastrowid

async def get_purchase_request(request_id: int) -> Optional[Dict[str, Any]]:
    """Получение заявки по ID"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM purchase_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

async def update_purchase_request_status(request_id: int, status: str):
    """Обновление статуса заявки"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE purchase_requests 
            SET status = ?, processed_at = ?
            WHERE id = ?
        ''', (status, now, request_id))
        conn.commit()

async def get_bot_stars_balance() -> int:
    """Получение баланса звезд бота"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM bot_stars_balance WHERE id = 1')
        result = cursor.fetchone()
        return result[0] if result else 0

async def update_bot_stars_balance(delta: int):
    """Обновление баланса звезд бота"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE bot_stars_balance SET balance = balance + ? WHERE id = 1', (delta,))
        conn.commit()

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Поиск пользователя по username (без @)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

async def get_all_pending_requests() -> List[Dict[str, Any]]:
    """Получение всех ожидающих заявок"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM purchase_requests WHERE status = "pending" ORDER BY created_at')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    

async def get_all_users() -> List[Dict[str, Any]]:
    """Получение всех пользователей"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY registration_date DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
# Добавьте в database.py

async def get_bot_stars_balance() -> int:
    """Получение баланса звезд бота"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM bot_stars_balance WHERE id = 1')
        result = cursor.fetchone()
        return result[0] if result else 0

async def update_bot_stars_balance(delta: int):
    """Обновление баланса звезд бота"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE bot_stars_balance SET balance = balance + ? WHERE id = 1', (delta,))
        conn.commit()