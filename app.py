import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, session, jsonify, render_template_string
import requests

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

DB_NAME = "data.db"

# -----------------------------
# DATABASE SETUP
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Orders table
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatnot_username TEXT,
            order_code TEXT,
            date TEXT,
            buy_amount REAL,
            sell_amount REAL,
            status TEXT
        )
    """)

    # Stocks table
    c.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity INTEGER,
            buy_price REAL,
            notes TEXT
        )
    """)

    # Visits table (IP + User-Agent + Geo)
    c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            timestamp TEXT,
            ip TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            device TEXT,
            browser TEXT,
            user_agent TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# DEVICE / BROWSER / GEO HELPERS
# -----------------------------
def parse_device(user_agent: str):
    ua = (user_agent or "").lower()
    device = "Unknown device"

    if "iphone" in ua:
        device = "iPhone"
    elif "ipad" in ua:
        device = "iPad"
    elif "android" in ua:
        device = "Android"
    elif "windows" in ua:
        device = "Windows PC"
    elif "macintosh" in ua or "mac os" in ua:
        device = "Mac"
    elif "linux" in ua:
        device = "Linux"

    return device

def parse_browser(user_agent: str):
    ua = (user_agent or "").lower()
    browser = "Unknown browser"

    if "edg" in ua:
        browser = "Microsoft Edge"
    elif "chrome" in ua and "safari" in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"

    return browser

def geo_lookup(ip: str):
    if not ip or ip in ("unknown", "127.0.0.1", "::1"):
        return {"country": "Unknown", "region": "", "city": ""}

    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "country": data.get("country_name") or "Unknown",
                "region": data.get("region") or "",
                "city": data.get("city") or ""
            }
    except:
        pass

    return {"country": "Unknown", "region": "", "city": ""}

# -----------------------------
# LOGGING
# -----------------------------
def log_event(event):
    try:
        ip = request.remote_addr or "unknown"
        ua = request.headers.get("User-Agent", "")
    except RuntimeError:
        ip = "unknown"
        ua = ""

    geo = geo_lookup(ip)
    device = parse_device(ua)
    browser = parse_browser(ua)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO visits (event, timestamp, ip, country, region, city, device, browser, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event,
            datetime.now().isoformat(timespec="seconds"),
            ip,
            geo["country"],
            geo["region"],
            geo["city"],
            device,
            browser,
            ua
        )
    )
    conn.commit()
    conn.close()

# -----------------------------
# AUTH HELPERS
# -----------------------------
def require_login():
    return bool(session.get("logged_in"))

# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == "admin" and pw == "admin":
            session["logged_in"] = True
            session["username"] = "admin"
            log_event("Admin logged in")
            return redirect("/dashboard?login=1")
        else:
            return """
            <script>alert('Invalid username or password');window.location='/'</script>
            """

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

        <style>
            body {
                background: linear-gradient(180deg, #ffe6f2, #ffffff);
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .login-card {
                width: 90%;
                max-width: 380px;
                padding: 30px;
                border-radius: 15px;
                background: white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .title {
                text-align: center;
                font-weight: bold;
                color: #ff4da6;
                margin-bottom: 20px;
            }
            .btn-main {
                background: #ff4da6;
                color: white;
                width: 100%;
            }
        </style>
    </head>

    <body>
        <div class="login-card">
            <h3 class="title">Seller Dashboard</h3>

            <form method="POST">
                <input name="username" class="form-control mb-3" placeholder="Username">
                <input name="password" type="password" class="form-control mb-3" placeholder="Password">
                <button type="submit" class="btn btn-main">Login</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(template)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------------
# NAVBAR
# -----------------------------
NAVBAR = """
<nav class="navbar navbar-dark shadow-sm" style="background:#ff4da6;">
  <div class="container-fluid">
    <div class="d-flex align-items-center">
        <img src="/icon-192.png" width="32" height="32" style="border-radius:10px;" class="me-2">
        <span class="navbar-brand fw-bold">{{ title }}</span>
    </div>
    <div class="d-flex gap-2">
        <a href="/dashboard" class="btn btn-sm btn-light">Dashboard</a>
        <a href="/orders" class="btn btn-sm btn-light">Orders</a>
        <a href="/stocks" class="btn btn-sm btn-light">Stocks</a>
        <a href="/profit" class="btn btn-sm btn-light">Profit</a>
        <a href="/admin" class="btn btn-sm btn-light">Admin</a>
        <a href="/logout" class="btn btn-sm btn-outline-light">Logout</a>
    </div>
  </div>
</nav>
"""

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect("/")

    log_event("Visited dashboard")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT SUM(sell_amount - buy_amount) FROM orders")
    profit = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM stocks")
    stock_count = c.fetchone()[0]

    conn.close()

    template = f"""
    {NAVBAR}
    <div class="container mt-4">
        <h3>Dashboard Overview</h3>
        <div class="row mt-3">
            <div class="col-4">
                <div class="p-3 bg-light rounded shadow-sm">
                    <h5>Total Orders</h5>
                    <p class="fs-3">{total_orders}</p>
                </div>
            </div>
            <div class="col-4">
                <div class="p-3 bg-light rounded shadow-sm">
                    <h5>Total Profit</h5>
                    <p class="fs-3">£{profit:.2f}</p>
                </div>
            </div>
            <div class="col-4">
                <div class="p-3 bg-light rounded shadow-sm">
                    <h5>Stock Items</h5>
                    <p class="fs-3">{stock_count}</p>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(template)

# -----------------------------
# ORDERS PAGE
# -----------------------------
@app.route("/orders")
def orders():
    if not require_login():
        return redirect("/")

    log_event("Visited orders")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>£{r[4]}</td><td>£{r[5]}</td><td>{r[6]}</td></tr>"
        for r in rows
    ])

    template = f"""
    {NAVBAR}
    <div class="container mt-4">
        <h3>Orders</h3>
        <table class="table table-striped mt-3">
            <tr><th>User</th><th>Code</th><th>Date</th><th>Buy</th><th>Sell</th><th>Status</th></tr>
            {table}
        </table>
    </div>
    """
    return render_template_string(template)

# -----------------------------
# STOCKS PAGE
# -----------------------------
@app.route("/stocks")
def stocks():
    if not require_login():
        return redirect("/")

    log_event("Visited stocks")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM stocks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>£{r[3]}</td><td>{r[4]}</td></tr>"
        for r in rows
    ])

    template = f"""
    {NAVBAR}
    <div class="container mt-4">
        <h3>Stocks</h3>
        <table class="table table-striped mt-3">
            <tr><th>Item</th><th>Qty</th><th>Buy Price</th><th>Notes</th></tr>
            {table}
        </table>
    </div>
    """
    return render_template_string(template)

# -----------------------------
# PROFIT PAGE
# -----------------------------
@app.route("/profit")
def profit():
    if not require_login():
        return redirect("/")

    log_event("Visited profit")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, SUM(sell_amount - buy_amount) FROM orders GROUP BY date")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[0]}</td><td>£{r[1]:.2f}</td></tr>"
        for r in rows
    ])

    template = f"""
    {NAVBAR}
    <div class="container mt-4">
        <h3>Daily Profit</h3>
        <table class="table table-striped mt-3">
            <tr><th>Date</th><th>Profit</th></tr>
            {table}
        </table>
    </div>
    """
    return render_template_string(template)

# -----------------------------
# ADMIN PAGE (VISIT LOGS)
# -----------------------------
@app.route("/admin")
def admin():
    if not require_login():
        return redirect("/")

    log_event("Visited admin")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT event, timestamp, ip, country, region, city, device, browser FROM visits ORDER BY id DESC LIMIT 200")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td><td>{r[7]}</td></tr>"
        for r in rows
    ])

    template = f"""
    {NAVBAR}
    <div class="container mt-4">
        <h3>Admin Logs</h3>
        <table class="table table-striped mt-3">
            <tr><th>Event</th><th>Time</th><th>IP</th><th>Country</th><th>Region</th><th>City</th><th>Device</th><th>Browser</th></tr>
            {table}
        </table>
    </div>
    """
    return render_template_string(template)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
