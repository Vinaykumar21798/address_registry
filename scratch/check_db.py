import sqlite3

def check():
    conn = sqlite3.connect("registry.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in database:", tables)
    conn.close()

if __name__ == "__main__":
    check()
