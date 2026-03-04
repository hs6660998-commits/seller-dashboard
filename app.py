import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, request, redirect, session,
    render_template_string, jsonify, url_for
)
import requests

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

DB_NAME = "data.db"

# -----------------------------
# DATABASE SETUP (FULL RESET)
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Drop old tables for a clean reset
    c.execute("DROP TABLE IF EXISTS orders")
    c.execute("DROP TABLE IF EXISTS stocks")
    c.execute("DROP TABLE IF EXISTS visits")

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatnot_username TEXT,
            order_code TEXT,
            date TEXT,
            buy_amount REAL,
            sell_amount REAL,
            profit REAL,
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
        return {"country": "Local", "region": "", "city": ""}

    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        if r.status_code == 200:
            d = r.json()
            if d.get("error"):
                return {"country": "Unknown", "region": "", "city": ""}
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

    # Ignore Render health checks and internal noise
    if (
        ip.startswith("10.") or
        ip.startswith("100.") or
        ip in ("127.0.0.1", "::1") or
        "render" in ua.lower() or
        "go-http-client" in ua.lower() or
        "curl" in ua.lower()
    ):
        return

    device = parse_device(ua)
    browser = parse_browser(ua)
    geo = geo_lookup(ip)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO visits (event, timestamp, ip, country, region, city, device, browser, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
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

def require_login():
    return bool(session.get("logged_in"))

# -----------------------------
# PUBLIC HOMEPAGE ( / )
# -----------------------------
@app.route("/")
def homepage():
    # log homepage visit
    log_event("Visited homepage")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT SUM(profit) FROM orders")
    total_profit = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM stocks")
    total_stock = c.fetchone()[0]
    conn.close()

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Gemzy's Wardrobe Wonders</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: 'Poppins', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
                color: white;
                text-align: center;
                background: linear-gradient(45deg, #ff0099, #8a00ff, #ff00cc);
                background-size: 600% 600%;
                animation: gradientMove 12s ease infinite;
            }
            @keyframes gradientMove {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            .container {
                animation: fadeIn 1.5s ease forwards;
                opacity: 0;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .logo {
                width: 150px;
                animation: float 3s ease-in-out infinite;
            }
            @keyframes float {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
                100% { transform: translateY(0px); }
            }
            .username {
                margin-top: 15px;
                font-size: 1.7rem;
                font-weight: 600;
            }
            .stats {
                margin-top: 30px;
                font-size: 1.1rem;
                line-height: 1.7rem;
            }
            .dashboard-btn {
                position: absolute;
                top: 20px;
                right: 20px;
                background: white;
                color: #ff00aa;
                padding: 10px 20px;
                border-radius: 30px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                transition: 0.2s;
            }
            .dashboard-btn:hover {
                background: #ffe6f7;
            }
            .site-icon {
                position: absolute;
                top: 20px;
                left: 20px;
                width: 55px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            }
        </style>
    </head>
    <body>
        <a href="{{ url_for('login') }}" class="dashboard-btn">Dashboard</a>
        <img src="{{ url_for('static', filename='icon-192.png') }}" class="site-icon">

        <div class="container">
            <img src="{{ url_for('static', filename='whatnot-icon.png') }}" class="logo">
            <div class="username">@gemzyswardrobewonders</div>
            <div class="stats">
                <div><b>Total Orders:</b> {{ total_orders }}</div>
                <div><b>Total Profit:</b> £{{ '%.2f' % total_profit }}</div>
                <div><b>Total Stock Items:</b> {{ total_stock }}</div>
            </div>
        </div>
    </body>
    </html>
    """, total_orders=total_orders, total_profit=total_profit, total_stock=total_stock)

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
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
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
        .btn-main { background:#ff4da6; color:white; }
    </style>
</head>
<body>
<div class="app-shell">
    <nav class="navbar navbar-dark navbar-custom shadow-sm">
      <div class="container-fluid">
        <div class="d-flex align-items-center">
            <img src="{{ url_for('static', filename='icon-192.png') }}" width="32" height="32" style="border-radius:10px;" class="me-2">
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
# LOGIN (NOW AT /login)
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "admin":
            session["logged_in"] = True
            log_event("Admin logged in")
            return redirect("/dashboard")
        return "<script>alert('Invalid credentials');window.location='/login'</script>"

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
    if not require_login():
        return redirect("/login")
    log_event("Visited dashboard")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    c.execute("SELECT SUM(profit) FROM orders")
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
# ORDERS (LIST + ADD + CHANGE STATUS)
# -----------------------------
@app.route("/orders", methods=["GET", "POST"])
def orders():
    if not require_login():
        return redirect("/login")
    log_event("Visited orders")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Handle new order (from modal)
    if request.method == "POST" and request.form.get("action") == "add_order":
        username = request.form.get("whatnot_username", "").strip()
        code = request.form.get("order_code", "").strip()
        buy = float(request.form.get("buy_amount") or 0)
        sell = float(request.form.get("sell_amount") or 0)
        profit = sell - buy
        date = datetime.now().strftime("%Y-%m-%d")
        status = "Processed"

        c.execute("""
            INSERT INTO orders (whatnot_username, order_code, date, buy_amount, sell_amount, profit, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, code, date, buy, sell, profit, status))
        conn.commit()

    c.execute("SELECT id, whatnot_username, order_code, date, buy_amount, sell_amount, profit, status FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    # Build table rows with inline modals
    table_rows = ""
    for r in rows:
        oid, user, code, date, buy, sell, profit, status = r
        modal_id = f"statusModal_{oid}"
        table_rows += f"""
        <tr id="order_row_{oid}">
            <td>{user}</td>
            <td>{code}</td>
            <td>{date}</td>
            <td>£{buy:.2f}</td>
            <td>£{sell:.2f}</td>
            <td>£{profit:.2f}</td>
            <td><span class="badge bg-secondary" id="status_badge_{oid}">{status}</span></td>
            <td>
                <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#{modal_id}">
                    Change Status
                </button>
            </td>
        </tr>

        <div class="modal fade" id="{modal_id}" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Change Status - {code}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <select class="form-select" id="status_select_{oid}">
                    <option value="Processed" {"selected" if status=="Processed" else ""}>Processed</option>
                    <option value="Shipped" {"selected" if status=="Shipped" else ""}>Shipped</option>
                    <option value="Delivered" {"selected" if status=="Delivered" else ""}>Delivered</option>
                </select>
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button class="btn btn-main" onclick="updateStatus({oid})">Save</button>
              </div>
            </div>
          </div>
        </div>
        """

    inner = f"""
    <div class='page-header'>
        <div><div class='page-title'>Orders</div></div>
        <button class="btn btn-main btn-sm" data-bs-toggle="modal" data-bs-target="#addOrderModal">Add Order</button>
    </div>

    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr>
                <th>User</th><th>Code</th><th>Date</th><th>Buy</th><th>Sell</th><th>Profit</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
                {table_rows or "<tr><td colspan='8' class='text-center text-muted'>No orders yet.</td></tr>"}
            </tbody>
        </table>
    </div>

    <!-- Add Order Modal -->
    <div class="modal fade" id="addOrderModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <form method="POST">
            <input type="hidden" name="action" value="add_order">
            <div class="modal-header">
              <h5 class="modal-title">Add Order</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div class="mb-2">
                <label class="form-label">Whatnot Username</label>
                <input name="whatnot_username" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Order ID</label>
                <input name="order_code" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Buy Amount (£)</label>
                <input name="buy_amount" type="number" step="0.01" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Sell Amount (£)</label>
                <input name="sell_amount" type="number" step="0.01" class="form-control" required>
              </div>
              <small class="text-muted">Profit will be calculated automatically.</small>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
              <button type="submit" class="btn btn-main">Save Order</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
    async function updateStatus(orderId) {{
        const select = document.getElementById('status_select_' + orderId);
        const newStatus = select.value;
        try {{
            const res = await fetch('/update_order_status', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{ id: orderId, status: newStatus }})
            }});
            const data = await res.json();
            if (data.success) {{
                const badge = document.getElementById('status_badge_' + orderId);
                badge.textContent = newStatus;
                badge.className = 'badge bg-secondary';
                var modalEl = document.getElementById('statusModal_' + orderId);
                var modal = bootstrap.Modal.getInstance(modalEl);
                modal.hide();
            }} else {{
                alert('Failed to update status');
            }}
        }} catch (e) {{
            alert('Error updating status');
        }}
    }}
    </script>
    """
    return render_page("Orders", inner)

@app.route("/update_order_status", methods=["POST"])
def update_order_status():
    if not require_login():
        return jsonify({"success": False}), 403
    data = request.get_json() or {}
    oid = data.get("id")
    status = data.get("status")
    if not oid or status not in ["Processed", "Shipped", "Delivered"]:
        return jsonify({"success": False}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
    conn.commit()
    conn.close()
    log_event(f"Changed order {oid} status to {status}")
    return jsonify({"success": True})

# -----------------------------
# STOCKS (LIST + ADD)
# -----------------------------
@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    if not require_login():
        return redirect("/login")
    log_event("Visited stocks")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST" and request.form.get("action") == "add_stock":
        name = request.form.get("item_name", "").strip()
        qty = int(request.form.get("quantity") or 0)
        buy_price = float(request.form.get("buy_price") or 0)
        notes = request.form.get("notes", "").strip()
        c.execute("""
            INSERT INTO stocks (item_name, quantity, buy_price, notes)
            VALUES (?, ?, ?, ?)
        """, (name, qty, buy_price, notes))
        conn.commit()

    c.execute("SELECT id, item_name, quantity, buy_price, notes FROM stocks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    table_rows = "".join([
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>£{r[3]:.2f}</td><td>{r[4]}</td></tr>"
        for r in rows
    ])

    inner = f"""
    <div class='page-header'>
        <div><div class='page-title'>Stocks</div></div>
        <button class="btn btn-main btn-sm" data-bs-toggle="modal" data-bs-target="#addStockModal">Add Stock</button>
    </div>

    <div class='table-responsive mt-2'>
        <table class='table align-middle'>
            <thead><tr>
                <th>Item</th><th>Qty</th><th>Buy Price</th><th>Notes</th>
            </tr></thead>
            <tbody>{table_rows or "<tr><td colspan='4' class='text-center text-muted'>No stock items yet.</td></tr>"}</tbody>
        </table>
    </div>

    <!-- Add Stock Modal -->
    <div class="modal fade" id="addStockModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <form method="POST">
            <input type="hidden" name="action" value="add_stock">
            <div class="modal-header">
              <h5 class="modal-title">Add Stock</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div class="mb-2">
                <label class="form-label">Item Name</label>
                <input name="item_name" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Quantity</label>
                <input name="quantity" type="number" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Buy Price (£)</label>
                <input name="buy_price" type="number" step="0.01" class="form-control" required>
              </div>
              <div class="mb-2">
                <label class="form-label">Notes</label>
                <textarea name="notes" class="form-control" rows="2"></textarea>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
              <button type="submit" class="btn btn-main">Save Stock</button>
            </div>
          </form>
        </div>
      </div>
    </div>
    """
    return render_page("Stocks", inner)

# -----------------------------
# PROFIT
# -----------------------------
@app.route("/profit")
def profit():
    if not require_login():
        return redirect("/login")
    log_event("Visited profit")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT date, SUM(profit) FROM orders GROUP BY date ORDER BY date DESC")
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
    if not require_login():
        return redirect("/login")
    log_event("Visited admin")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT event, timestamp, ip, country, region, city, device, browser
        FROM visits
        ORDER BY id DESC LIMIT 200
    """)
    rows = c.fetchall()
    conn.close()

    table = ""
    for event, ts, ip, country, region, city, device, browser in rows:
        loc_parts = [city, region, country]
        loc = ", ".join([p for p in loc_parts if p]).strip() or "Unknown"
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
