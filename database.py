import sqlite3
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных операций"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    # Таблица агентов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        codename TEXT,
        real_name TEXT,
        is_keeper BOOLEAN DEFAULT FALSE,
        clearance_level TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица кладовых
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lockers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keeper_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        access_code TEXT UNIQUE,
        FOREIGN KEY (keeper_id) REFERENCES agents (id) ON DELETE CASCADE
    )
    ''')
    
    # Таблица улик
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        locker_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        dossier TEXT,
        location TEXT,
        estimated_value TEXT,
        photo_id TEXT,
        status TEXT DEFAULT 'available',
        taken_by INTEGER,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (locker_id) REFERENCES lockers (id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("🕵️‍♂️ База данных 'Кладовая улик' инициализирована")

def add_user(telegram_id, username=None, first_name=None, is_admin=False):
    """Регистрация агента в системе"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT OR IGNORE INTO agents (telegram_id, codename, real_name, is_keeper) VALUES (?, ?, ?, ?)',
            (telegram_id, username, first_name, is_admin)
        )
        
        if cursor.rowcount > 0:
            agent_id = cursor.lastrowid
            access_code = str(uuid.uuid4())[:8]
            
            cursor.execute(
                'INSERT INTO lockers (keeper_id, access_code) VALUES (?, ?)',
                (agent_id, access_code)
            )
        
        conn.commit()
        logger.info(f"🕵️‍♂️ Агент {telegram_id} зарегистрирован")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации агента: {e}")
        return False
    finally:
        conn.close()

def get_or_create_locker(telegram_id):
    """Получить или создать кладовую для агента"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM agents WHERE telegram_id = ?', (telegram_id,))
    agent = cursor.fetchone()
    
    if not agent:
        conn.close()
        return None
    
    agent_id = agent[0]
    
    cursor.execute('SELECT id FROM lockers WHERE keeper_id = ?', (agent_id,))
    locker = cursor.fetchone()
    
    if not locker:
        access_code = str(uuid.uuid4())[:8]
        cursor.execute(
            'INSERT INTO lockers (keeper_id, access_code) VALUES (?, ?)',
            (agent_id, access_code)
        )
        locker_id = cursor.lastrowid
        conn.commit()
    else:
        locker_id = locker[0]
    
    conn.close()
    return locker_id

def add_item(telegram_id, title, description="", link="", price_range="", photo_id=None):
    """Занесение новой улики в базу"""
    locker_id = get_or_create_locker(telegram_id)
    
    if not locker_id:
        return False
    
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO evidence (locker_id, title, dossier, location, estimated_value, photo_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (locker_id, title, description, link, price_range, photo_id))
        
        conn.commit()
        logger.info(f"📁 Улика '{title}' занесена в базу")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"❌ Ошибка занесения улики: {e}")
        return False
    finally:
        conn.close()

def get_user_items(telegram_id):
    """Получить список улик агента"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT l.id FROM lockers l
    JOIN agents a ON l.keeper_id = a.id
    WHERE a.telegram_id = ?
    ''', (telegram_id,))
    
    locker = cursor.fetchone()
    
    if not locker:
        conn.close()
        return []
    
    locker_id = locker[0]
    
    cursor.execute('''
    SELECT id, title, dossier, location, estimated_value, photo_id, status, taken_by
    FROM evidence
    WHERE locker_id = ?
    ORDER BY logged_at DESC
    ''', (locker_id,))
    
    items = cursor.fetchall()
    conn.close()
    
    result = []
    for item in items:
        result.append({
            'id': item[0],
            'title': item[1],
            'description': item[2],
            'link': item[3],
            'price_range': item[4],
            'photo_id': item[5],
            'status': item[6],
            'reserved_by': item[7]
        })
    
    return result

def reserve_item(item_id, telegram_id):
    """Взятие улики в работу"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT status FROM evidence WHERE id = ?', (item_id,))
        evidence = cursor.fetchone()
        
        if not evidence:
            return "item_not_found"
        
        if evidence[0] != 'available':
            return "already_reserved"
        
        cursor.execute(
            'UPDATE evidence SET status = "reserved", taken_by = ? WHERE id = ?',
            (telegram_id, item_id)
        )
        
        conn.commit()
        logger.info(f"✅ Улика {item_id} взята в работу агентом {telegram_id}")
        return "success"
    except Exception as e:
        logger.error(f"❌ Ошибка при взятии улики: {e}")
        return "error"
    finally:
        conn.close()

def get_item_by_id(item_id):
    """Получить информацию об улике"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, dossier, location, estimated_value, photo_id, status, taken_by
    FROM evidence
    WHERE id = ?
    ''', (item_id,))
    
    item = cursor.fetchone()
    conn.close()
    
    if item:
        return {
            'id': item[0],
            'title': item[1],
            'description': item[2],
            'link': item[3],
            'price_range': item[4],
            'photo_id': item[5],
            'status': item[6],
            'reserved_by': item[7]
        }
    return None

def get_share_token(telegram_id):
    """Получить код доступа к кладовой"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT l.access_code FROM lockers l
    JOIN agents a ON l.keeper_id = a.id
    WHERE a.telegram_id = ?
    ''', (telegram_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def get_wishlist_by_token(token):
    """Найти кладовую по коду доступа"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT a.telegram_id, a.real_name, l.id
    FROM lockers l
    JOIN agents a ON l.keeper_id = a.id
    WHERE l.access_code = ? AND l.is_active = TRUE
    ''', (token,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'owner_id': result[0],
            'owner_name': result[1],
            'wishlist_id': result[2]
        }
    return None

def get_items_by_wishlist_id(wishlist_id):
    """Получить все улики из кладовой"""
    conn = sqlite3.connect('evidence_locker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, title, dossier, location, estimated_value, photo_id, status
    FROM evidence
    WHERE locker_id = ? AND status != 'closed'
    ORDER BY logged_at DESC
    ''', (wishlist_id,))
    
    items = cursor.fetchall()
    conn.close()
    
    result = []
    for item in items:
        result.append({
            'id': item[0],
            'title': item[1],
            'description': item[2],
            'link': item[3],
            'price_range': item[4],
            'photo_id': item[5],
            'status': item[6]
        })
    
    return result

# Инициализация базы при импорте
init_db()
