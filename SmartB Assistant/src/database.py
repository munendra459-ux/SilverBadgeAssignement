"""SQL database layer for persistent data storage."""
import sqlite3
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / "database" / "smartb.db"

def init_db():
    """Initialize database tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sales transactions
    cursor.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY,
        order_id TEXT UNIQUE,
        order_date TEXT,
        ship_date TEXT,
        customer_id TEXT,
        product_id TEXT,
        category TEXT,
        sales REAL,
        quantity INTEGER,
        profit REAL,
        shipping_cost REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Customer feedback
    cursor.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY,
        review_id TEXT UNIQUE,
        order_id TEXT,
        customer_id TEXT,
        product_id TEXT,
        rating INTEGER,
        review_text TEXT,
        sentiment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Inventory tracking
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY,
        product_id TEXT UNIQUE,
        product_name TEXT,
        category TEXT,
        stock_quantity INTEGER,
        reorder_level INTEGER,
        unit_cost REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Marketing campaigns
    cursor.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY,
        campaign_id TEXT UNIQUE,
        campaign_name TEXT,
        start_date TEXT,
        end_date TEXT,
        budget REAL,
        channel TEXT,
        target_audience TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Campaign performance
    cursor.execute("""CREATE TABLE IF NOT EXISTS campaign_performance (
        id INTEGER PRIMARY KEY,
        campaign_id TEXT,
        date TEXT,
        impressions INTEGER,
        clicks INTEGER,
        conversions INTEGER,
        revenue REAL,
        cost REAL,
        FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id)
    )""")
    
    # Competitor tracking
    cursor.execute("""CREATE TABLE IF NOT EXISTS competitors (
        id INTEGER PRIMARY KEY,
        competitor_id TEXT UNIQUE,
        competitor_name TEXT,
        category TEXT,
        market_share REAL,
        avg_price REAL,
        avg_rating REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Market data
    cursor.execute("""CREATE TABLE IF NOT EXISTS market_trends (
        id INTEGER PRIMARY KEY,
        date TEXT,
        category TEXT,
        market_demand REAL,
        avg_price REAL,
        growth_rate REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Scheduled reports
    cursor.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY,
        report_id TEXT UNIQUE,
        report_type TEXT,
        frequency TEXT,
        generated_date TEXT,
        filepath TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Transaction lines are deliberately separate from the legacy sales table:
    # an order can contain multiple products, so order_id cannot be unique here.
    cursor.execute("""CREATE TABLE IF NOT EXISTS sales_transactions (
        line_id TEXT PRIMARY KEY,
        order_id TEXT,
        order_date TEXT,
        ship_date TEXT,
        customer_id TEXT,
        product_id TEXT,
        category TEXT,
        sales REAL,
        quantity INTEGER,
        profit REAL,
        shipping_cost REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()

def insert_sales(df):
    """Persist transaction lines without discarding additional lines per order."""
    import hashlib
    init_db()
    if df.empty:
        return 0
    conn = sqlite3.connect(DB_PATH)
    rows = []
    for index, row in df.iterrows():
        line_key = "|".join(str(row.get(column, "")) for column in
                            ('order_id', 'order_date', 'product_id', 'sales', 'quantity'))
        line_id = hashlib.sha256(f"{index}|{line_key}".encode()).hexdigest()
        rows.append((line_id, row.get('order_id'), row.get('order_date'), row.get('ship_date'),
                     row.get('customer_id'), row.get('product_id'), row.get('category'),
                     row.get('sales', 0), row.get('quantity', 1), row.get('profit', 0),
                     row.get('shipping_cost', 0)))
    conn.executemany("""INSERT OR REPLACE INTO sales_transactions
        (line_id, order_id, order_date, ship_date, customer_id, product_id, category,
         sales, quantity, profit, shipping_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
    conn.commit()
    conn.close()
    return len(rows)


def upsert_inventory(df):
    """Save inventory rows from the UI's CSV template/upload."""
    init_db()
    rows = []
    for _, row in df.iterrows():
        rows.append((str(row['product_id']), row.get('product_name', row.get('product', 'Unspecified')),
                     row.get('category', 'Unspecified'), int(row['stock_quantity']),
                     int(row['reorder_level']), float(row['unit_cost'])))
    conn = sqlite3.connect(DB_PATH)
    conn.executemany("""INSERT OR REPLACE INTO inventory
        (product_id, product_name, category, stock_quantity, reorder_level, unit_cost)
        VALUES (?, ?, ?, ?, ?, ?)""", rows)
    conn.commit()
    conn.close()
    return len(rows)

def insert_feedback(df):
    """Insert feedback data into database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        try:
            conn.execute("""INSERT OR IGNORE INTO feedback 
                (review_id, order_id, customer_id, product_id, rating, review_text, sentiment)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (row.get('review_id'), row.get('order_id'), row.get('customer_id'),
                 row.get('product_id'), row.get('rating', 0), row.get('review_text', ''),
                 row.get('sentiment', 'Neutral')))
        except Exception:
            pass
    conn.commit()
    conn.close()

def insert_inventory(product_id, product_name, category, stock_quantity, reorder_level, unit_cost):
    """Insert or update inventory."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT OR REPLACE INTO inventory 
        (product_id, product_name, category, stock_quantity, reorder_level, unit_cost)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (product_id, product_name, category, stock_quantity, reorder_level, unit_cost))
    conn.commit()
    conn.close()

def get_inventory():
    """Retrieve all inventory data."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

def insert_campaign(campaign_id, campaign_name, start_date, end_date, budget, channel, target_audience):
    """Insert campaign data."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT OR REPLACE INTO campaigns 
        (campaign_id, campaign_name, start_date, end_date, budget, channel, target_audience)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (campaign_id, campaign_name, start_date, end_date, budget, channel, target_audience))
    conn.commit()
    conn.close()

def insert_campaign_performance(campaign_id, date, impressions, clicks, conversions, revenue, cost):
    """Insert campaign performance data."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO campaign_performance 
        (campaign_id, date, impressions, clicks, conversions, revenue, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (campaign_id, date, impressions, clicks, conversions, revenue, cost))
    conn.commit()
    conn.close()

def get_campaign_roi(campaign_id):
    """Calculate ROI for a campaign."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT SUM(cost) as total_cost, SUM(revenue) as total_revenue FROM campaign_performance WHERE campaign_id=?",
        conn, params=(campaign_id,))
    conn.close()
    if df.empty or df['total_cost'][0] == 0:
        return 0
    total_cost = df['total_cost'][0] or 0
    total_revenue = df['total_revenue'][0] or 0
    return ((total_revenue - total_cost) / total_cost) * 100 if total_cost > 0 else 0

def insert_competitor(competitor_id, competitor_name, category, market_share, avg_price, avg_rating):
    """Insert competitor data."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT OR REPLACE INTO competitors 
        (competitor_id, competitor_name, category, market_share, avg_price, avg_rating)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (competitor_id, competitor_name, category, market_share, avg_price, avg_rating))
    conn.commit()
    conn.close()

def get_competitors(category):
    """Retrieve competitors in a category."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM competitors WHERE category=? ORDER BY market_share DESC", 
                           conn, params=(category,))
    conn.close()
    return df

def insert_market_trend(date, category, market_demand, avg_price, growth_rate):
    """Insert market trend data."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO market_trends 
        (date, category, market_demand, avg_price, growth_rate)
        VALUES (?, ?, ?, ?, ?)""",
        (date, category, market_demand, avg_price, growth_rate))
    conn.commit()
    conn.close()

def get_market_trends(category, days=90):
    """Retrieve market trends for category."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    df = pd.read_sql_query(
        "SELECT * FROM market_trends WHERE category=? AND date >= ? ORDER BY date DESC",
        conn, params=(category, cutoff_date))
    conn.close()
    return df

def save_report(report_type, frequency, filepath):
    """Save report metadata."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    report_id = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conn.execute("""INSERT INTO reports 
        (report_id, report_type, frequency, generated_date, filepath, status)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (report_id, report_type, frequency, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         filepath, 'generated'))
    conn.commit()
    conn.close()
    return report_id

def get_recent_reports(limit=10):
    """Get recent reports."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", 
                           conn, params=(limit,))
    conn.close()
    return df
