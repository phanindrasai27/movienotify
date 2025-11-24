import sqlite3
import os

DB_FILE = 'data/movies.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Movies Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            city TEXT NOT NULL,
            language TEXT,
            format TEXT,
            UNIQUE(slug, city)
        )
    ''')
    
    # Theatres Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS theatres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            slug TEXT,
            UNIQUE(name, city)
        )
    ''')
    
    # Showtimes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS showtimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            theatre_id INTEGER,
            show_date TEXT NOT NULL, -- YYYY-MM-DD
            show_time TEXT NOT NULL,
            link TEXT,
            FOREIGN KEY (movie_id) REFERENCES movies (id),
            FOREIGN KEY (theatre_id) REFERENCES theatres (id),
            UNIQUE(movie_id, theatre_id, show_date, show_time)
        )
    ''')
    
    # Tracking Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_pattern TEXT, -- Regex or partial match
            theatre_pattern TEXT,
            format_pattern TEXT,
            city TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            last_notified_at DATETIME
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")

if __name__ == "__main__":
    init_db()
