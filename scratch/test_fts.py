import sqlite3

def run_test():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE VIRTUAL TABLE t USING fts5(x);")
    cur.execute("INSERT INTO t(x) VALUES ('123 Main Street');")
    cur.execute("INSERT INTO t(x) VALUES ('456 Main Ave');")
    
    # Try different search patterns
    patterns = [
        "Main* Stre*",
        "Main Stre*",
        "\"Main\"* AND \"Stre\"*",
        "Main AND Stre"
    ]
    
    for pattern in patterns:
        try:
            cur.execute("SELECT * FROM t WHERE t MATCH ?", (pattern,))
            results = cur.fetchall()
            print(f"Pattern: {pattern} -> Results: {results}")
        except Exception as e:
            print(f"Pattern: {pattern} -> Failed: {e}")

if __name__ == "__main__":
    run_test()
