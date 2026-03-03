import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, session, render_template_string
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity INTEGER,
            buy_price REAL,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            timestamp TEXT,
            ip TEXT,
            user_agent TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# HELPERS
# -----------------------------
def parse_device(ua):
    ua = (ua or "").lower()
    if "iphone" in ua: return "iPhone"
    if "ipad" in ua: return "iPad"
    if "android" in ua: return "Android"
    if "windows" in ua: return "Windows PC"
    if "macintosh" in ua or "mac os" in ua: return "Mac"
    if "linux" in ua: return "Linux"
    return "Unknown"

def parse_browser(ua):
    ua = (ua or "").lower()
    if "edg" in ua: return "Edge"
    if "chrome" in ua and "safari" in ua: return "Chrome"
    if "safari" in ua and "chrome" not in ua: return "Safari"
    if "firefox" in ua: return "Firefox"
    if "opr" in ua or "opera" in ua: return "Opera"
    return "Unknown"

def geo_lookup(ip):
    if not ip or ip in ("127.0.0.1", "::1", "unknown"):
        return {"country": "Unknown", "region": "", "city": ""}

    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        if r.status_code == 200:
            d = r.json()
            return {
                "country": d.get("country_name") or "Unknown",
                "region": d.get("region") or "",
                "city": d.get("city") or ""
            }
    except:
        pass

    return {"country": "Unknown", "region": "", "city": ""}

def log_event(event):
    try:
        ip = (
            request.headers.get("X-Forwarded-For")
            or request.headers.get("X-Real-IP")
            or request.remote_addr
            or "unknown"
        ).split(",")[0].strip()

        ua = request.headers.get("User-Agent", "")
    except RuntimeError:
        ip = "unknown"
        ua = ""

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO visits (event, timestamp, ip, user_agent) VALUES (?, ?, ?, ?)",
        (event, datetime.now().isoformat(timespec="seconds"), ip, ua)
    )
    conn.commit()
    conn.close()

def require_login():
    return bool(session.get("logged_in"))

# -----------------------------
# BASE HTML
# -----------------------------
BASE_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }} - Seller Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(180deg, #ffe6f2, #ffffff);
            min-height: 100vh;
        }
        .app-shell {
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            min-height: 100vh;
            box-shadow: 0 0 20px rgba(0,0,0,0.06);
        }
        .navbar-custom { background:#ff4da6; }
        .navbar-brand { font-weight: 700; }
        .nav-btn { border-radius: 999px; padding: 4px 10px; font-size: 0.8rem; }
        .card-metric { border-radius: 16px; background: #fff5fb; border: 1px solid #ffd1ec; }
        .card-metric h5 { font-size: 0.9rem; color: #ff4da6; text-transform: uppercase; }
        .card-metric .value { font-size: 1.8rem; font-weight: 700; color: #333; }
        .page-header { display:flex; justify-content:space-between; align-items:center; margin-top:1.5rem; margin-bottom:1rem; }
        .page-title { font-weight:700; font-size:1.3rem; }
        .pill-badge { border-radius:999px; padding:2px 10px; font-size:0.75rem; background:#ffe6f7; color:#ff4da6; }
        table thead { background:#fff0f8; }
        table thead th { border-bottom:2px solid #ffd1ec !important; font-size:0.8rem; text-transform:uppercase; color:#ff4da6; }
        table tbody td { font-size:0.85rem; vertical-align:middle; }
    </style>
</head>
<body>
<div class="app-shell">
    <nav class="navbar navbar-dark navbar-custom shadow-sm">
      <div class="container-fluid">
        <div class="d-flex align-items-center">
            <img src="/icon-192.png" width="32" height="32" style="border-radius:10px;" class="me-2">
            <span class="navbar-brand">{{ title }}</span>
        </div>
        <div class="d-flex gap-1">
            <a href="/dashboard" class="btn btn-sm btn-light nav-btn">Dashboard</a>
            <a href="/orders" class="btn btn-sm btn-light nav-btn">Orders</a>
            <a href="/stocks" class="btn btn-sm btn-light nav-btn">Stocks</a>
            <a href="/profit" class="btn btn-sm btn-light nav-btn">Profit</a>
            <a href="/admin" class="btn btn-sm btn-light nav-btn">Admin</a>
            <a href="/logout" class="btn btn-sm btn-outline-light nav-btn">Logout</a>
        </div>
      </div>
    </nav>

    <div class="container py-3">
        {{ content|safe }}
    </div>
</div>
</body>
</html>
"""

def render_page(title, inner_html):
    return render_template_string(BASE_HTML, title=title, content=inner_html)

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "admin":
            session["logged_in"] = True
            log_event("Admin logged in")
            return redirect("/dashboard")
        return "<script>alert('Invalid credentials');window.location='/'</script>"

    return render_template_string("""
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(180deg,#ffe6f2,#fff); height:100vh; display:flex; justify-content:center; align-items:center; }
        .login-card { width:90%; max-width:380px; padding:30px; border-radius:15px; background:white; box-shadow:0 4px 12px rgba(0,0,0,0.1); }
        .title { text-align:center; font-weight:bold; color:#ff4da6; margin-bottom:20px; }
        .btn-main { background:#ff4da6; color:white; width:100%; }
    </style>
    </head><body>
    <div class="login-card">
        <h3 class="title">Seller Dashboard</h3>
        <form method="POST">
            <input name="username" class="form-control mb-3" placeholder="Username">
            <input name="password" type="password" class="form-control mb-3" placeholder="Password">
            <button class="btn btn-main">Login</button>
        </form>
    </div>
    </body></html>
    """)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if not require_login(): return redirect("/")
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

    inner = f"""
    <div class='page-header'>
        <div>
            <div class='page-title'>Overview</div>
            <div class='text-muted' style='font-size:0.85rem;'>Quick snapshot of your selling performance</div>
        </div>
        <span class='pill-badge'>Live session</span>
    </div>

    <div class='row g-3 mt-1'>
        <div class='col-12 col-md-4'>
            <div class='p-3 card-metric'>
                <h5>Orders</h5>
                <div class='value'>{total_orders}</div>
            </div>
        </div>
        <div class='col-12 col-md-4'>
            <div class='p-3 card-metric'>
                <h5>Profit</h5>
                <div class='value'>£{profit:.2f}</div>
            </div>
        </div>
        <div class='col-12 col-md-4'>
            <div class='p-3 card-metric'>
                <h5>Stock Items</h5>
                <div class='value'>{stock_count}</div>
            </div>
        </div>
    </div>
    """
    return render_page("Dashboard", inner)

# -----------------------------
# ORDERS
# -----------------------------
@app.route("/orders")
def orders():
    if not require_login(): return redirect("/")
    log_event("Visited orders")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>£{r[4]:.2f}</td><td>£{r[5]:.2f}</td><td>{r[6]}</td></tr>"
        for r in rows
    ])

    inner = f"""
    <div class='page-header'><div><div class='page-title'>Orders</div></div></div>
    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr>
                <th>User</th><th>Code</th><th>Date</th><th>Buy</th><th>Sell</th><th>Status</th>
            </tr></thead>
            <tbody>{table or "<tr><td colspan='6' class='text-center text-muted'>No orders yet.</td></tr>"}</tbody>
        </table>
    </div>
    """
    return render_page("Orders", inner)

# -----------------------------
# STOCKS
# -----------------------------
@app.route("/stocks")
def stocks():
    if not require_login(): return redirect("/")
    log_event("Visited stocks")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM stocks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>£{r[3]:.2f}</td><td>{r[4]}</td></tr>"
        for r in rows
    ])

    inner = f"""
    <div class='page-header'><div><div class='page-title'>Stocks</div></div></div>
    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr>
                <th>Item</th><th>Qty</th><th>Buy Price</th><th>Notes</th>
            </tr></thead>
            <tbody>{table or "<tr><td colspan='4' class='text-center text-muted'>No stock items yet.</td></tr>"}</tbody>
        </table>
    </div>
    """
    return render_page("Stocks", inner)

# -----------------------------
# PROFIT
# -----------------------------
@app.route("/profit")
def profit():
    if not require_login(): return redirect("/")
    log_event("Visited profit")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, SUM(sell_amount - buy_amount) FROM orders GROUP BY date ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()

    table = "".join([
        f"<tr><td>{r[0]}</td><td>£{r[1]:.2f}</td></tr>"
        for r in rows
    ])

    inner = f"""
    <div class='page-header'><div><div class='page-title'>Daily Profit</div></div></div>
    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr><th>Date</th><th>Profit</th></tr></thead>
            <tbody>{table or "<tr><td colspan='2' class='text-center text-muted'>No profit data yet.</td></tr>"}</tbody>
        </table>
    </div>
    """
    return render_page("Profit", inner)

# -----------------------------
# ADMIN
# -----------------------------
@app.route("/admin")
def admin():
    if not require_login(): return redirect("/")
    log_event("Visited admin")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT event, timestamp, ip, user_agent FROM visits ORDER BY id DESC LIMIT 200")
    rows = c.fetchall()
    conn.close()

    table = ""
    for event, ts, ip, ua in rows:
        geo = geo_lookup(ip)
        device = parse_device(ua)
        browser = parse_browser(ua)
        loc = f"{geo['city']}, {geo['region']}, {geo['country']}".strip(", ").strip()
        if not loc: loc = "Unknown"

        table += f"""
        <tr>
            <td>{event}</td>
            <td>{ts}</td>
            <td>{ip}</td>
            <td>{loc}</td>
            <td>{device}</td>
            <td>{browser}</td>
        </tr>
        """

    inner = f"""
    <div class='page-header'><div><div class='page-title'>Admin Logs</div></div></div>
    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr>
                <th>Event</th><th>Time</th><th>IP</th><th>Location</th><th>Device</th><th>Browser</th>
            </tr></thead>
            <tbody>{table or "<tr><td colspan='6' class='text-center text-muted'>No logs yet.</td></tr>"}</tbody>
        </table>
    </div>
    """
    return render_page("Admin", inner)

# -----------------------------
# RUN (RENDER-SAFE)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
