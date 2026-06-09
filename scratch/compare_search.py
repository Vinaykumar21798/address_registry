import sqlite3
import random
import time

def generate_fake_addresses(count=10000):
    streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Cedar Ln", "Elm St", "View Rd", "Park Pl", "Sunset Blvd", "Broadway", "Highland Ave", "Washington St", "Second St", "Park Ave", "River Rd"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "San Francisco", "Indianapolis", "Columbus"]
    states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA", "TX", "FL", "CA", "IN", "OH"]
    zips = ["10001", "90001", "60601", "77001", "85001", "19101", "78201", "92101", "75201", "95101", "78701", "32201", "94101", "46201", "43201"]
    
    addresses = []
    # Seed random for reproducibility
    random.seed(42)
    for _ in range(count):
        num = random.randint(1, 9999)
        street = random.choice(streets)
        city = random.choice(cities)
        state = random.choice(states)
        zip_code = random.choice(zips)
        
        # We construct both normalized and raw formats
        raw = f"{num} {street}, {city}, {state} {zip_code}"
        normalized = f"{num} {street.upper()}, {city.upper()}, {state} {zip_code}".replace(",", "")
        addresses.append((raw, normalized, city, state, zip_code))
    return addresses

def setup_databases(addresses):
    # We will use two separate temporary SQLite connections to avoid interference
    # Database for LIKE search
    conn_like = sqlite3.connect(":memory:")
    conn_like.execute("""
        CREATE TABLE addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT,
            normalized TEXT,
            city TEXT,
            state TEXT,
            zip TEXT
        );
    """)
    conn_like.execute("CREATE INDEX idx_addresses_normalized ON addresses(normalized);")
    conn_like.executemany("INSERT INTO addresses(raw_text, normalized, city, state, zip) VALUES (?, ?, ?, ?, ?)", addresses)
    conn_like.commit()
    
    # Database for FTS5 search
    conn_fts = sqlite3.connect(":memory:")
    conn_fts.execute("""
        CREATE TABLE addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT,
            normalized TEXT,
            city TEXT,
            state TEXT,
            zip TEXT
        );
    """)
    conn_fts.execute("CREATE VIRTUAL TABLE addresses_fts USING fts5(id UNINDEXED, raw_text);")
    
    # Define triggers for sync
    conn_fts.execute("""
        CREATE TRIGGER address_after_insert AFTER INSERT ON addresses BEGIN
            INSERT INTO addresses_fts(id, raw_text) VALUES (new.id, new.raw_text);
        END;
    """)
    
    # Insert addresses which will trigger automatic insertion into FTS5
    conn_fts.executemany("INSERT INTO addresses(raw_text, normalized, city, state, zip) VALUES (?, ?, ?, ?, ?)", addresses)
    conn_fts.commit()
    
    return conn_like, conn_fts

def run_performance_test():
    addresses = generate_fake_addresses(10000)
    conn_like, conn_fts = setup_databases(addresses)
    
    queries = [
        # (Label, LIKE SQL, FTS5 SQL, Query Term)
        ("Single Word Search",
         "SELECT * FROM addresses WHERE normalized LIKE ?",
         "SELECT addresses.* FROM addresses JOIN addresses_fts ON addresses.id = addresses_fts.id WHERE addresses_fts MATCH ?",
         "Main"),
         
        ("Prefix Search (starts with)",
         "SELECT * FROM addresses WHERE normalized LIKE ?",
         "SELECT addresses.* FROM addresses JOIN addresses_fts ON addresses.id = addresses_fts.id WHERE addresses_fts MATCH ?",
         "Sun"),
         
        ("Multi-word Query",
         "SELECT * FROM addresses WHERE normalized LIKE ? AND normalized LIKE ?",
         "SELECT addresses.* FROM addresses JOIN addresses_fts ON addresses.id = addresses_fts.id WHERE addresses_fts MATCH ?",
         "Broadway Austin"),
         
        ("Common Term (High Hits)",
         "SELECT * FROM addresses WHERE normalized LIKE ?",
         "SELECT addresses.* FROM addresses JOIN addresses_fts ON addresses.id = addresses_fts.id WHERE addresses_fts MATCH ?",
         "Ave")
    ]
    
    iterations = 500
    
    print("| Query Type | Search Term | Results Count (LIKE) | Results Count (FTS5) | LIKE Time (ms) | FTS5 Time (ms) | Speedup Factor |")
    print("|------------|-------------|----------------------|----------------------|----------------|----------------|----------------|")
    
    for label, sql_like, sql_fts, term in queries:
        # 1. Measure Results Count & Run LIKE
        cur_like = conn_like.cursor()
        
        # Prepare parameters for LIKE
        if label == "Multi-word Query":
            words = term.split()
            like_params = (f"%{words[0]}%", f"%{words[1]}%")
        else:
            like_params = (f"%{term}%",)
            
        cur_like.execute(sql_like, like_params)
        results_like = cur_like.fetchall()
        count_like = len(results_like)
        
        # Measure LIKE Time
        t0 = time.perf_counter()
        for _ in range(iterations):
            cur_like.execute(sql_like, like_params)
            cur_like.fetchall()
        time_like = (time.perf_counter() - t0) * 1000 / iterations
        
        # 2. Measure Results Count & Run FTS5
        cur_fts = conn_fts.cursor()
        
        # Prepare parameters for FTS5
        words = term.split()
        fts_term = " AND ".join(f'"{w}"*' for w in words)
        
        cur_fts.execute(sql_fts, (fts_term,))
        results_fts = cur_fts.fetchall()
        count_fts = len(results_fts)
        
        # Measure FTS5 Time
        t0 = time.perf_counter()
        for _ in range(iterations):
            cur_fts.execute(sql_fts, (fts_term,))
            cur_fts.fetchall()
        time_fts = (time.perf_counter() - t0) * 1000 / iterations
        
        speedup = time_like / time_fts if time_fts > 0 else 0
        print(f"| {label} | `{term}` | {count_like} | {count_fts} | {time_like:.4f} ms | {time_fts:.4f} ms | {speedup:.2f}x |")
        
    conn_like.close()
    conn_fts.close()

if __name__ == "__main__":
    print("Running Address Search Comparison (10,000 Records, 500 Iterations)...")
    run_performance_test()
