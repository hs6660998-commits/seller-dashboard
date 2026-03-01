from flask import Flask, request, redirect, session, jsonify, render_template_string
import sqlite3
from datetime import datetime

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

    # Visits / logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

def log_event(event):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO visits (event, timestamp) VALUES (?, ?)",
              (event, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# AUTH HELPERS
# -----------------------------
def require_login():
    return bool(session.get("logged_in"))

# -----------------------------
# PWA ROUTES
# -----------------------------
@app.route("/manifest.json")
def manifest():
    return {
        "name": "Seller Dashboard",
        "short_name": "Dashboard",
        "start_url": "/dashboard",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#ff4da6",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }

@app.route("/service-worker.js")
def service_worker():
    js = """
self.addEventListener("install", (event) => {
  self.skipWaiting();
});
self.addEventListener("activate", (event) => {
  clients.claim();
});
self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
"""
    return app.response_class(js, mimetype="application/javascript")

@app.route("/icon-192.png")
def icon_192():
    return app.send_static_file("icon-192.png")

@app.route("/icon-512.png")
def icon_512():
    return app.send_static_file("icon-512.png")

# -----------------------------
# LOGIN
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

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

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
# NAVBAR TEMPLATE SNIPPET
# -----------------------------
NAVBAR = """
<nav class="navbar navbar-dark" style="background:#ff4da6;">
  <div class="container-fluid">
    <div class="d-flex align-items-center">
        <img src="/icon-192.png" width="32" height="32"
             style="border-radius:10px;" class="me-2">
        <span class="navbar-brand">{{ title }}</span>
    </div>
    <div>
        <a href="/dashboard" class="btn btn-sm btn-light me-2">Dashboard</a>
        <a href="/orders" class="btn btn-sm btn-light me-2">Orders</a>
        <a href="/stocks" class="btn btn-sm btn-light me-2">Stocks</a>
        <a href="/profit" class="btn btn-sm btn-light me-2">Profit</a>
        <a href="/admin" class="btn btn-sm btn-light me-2">Admin</a>
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

    log_event("Dashboard opened")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*), COALESCE(SUM(sell_amount - buy_amount), 0) FROM orders")
    row = c.fetchone()
    total_orders = row[0] or 0
    total_profit = row[1] or 0

    c.execute("SELECT COUNT(*) FROM stocks")
    stock_count = c.fetchone()[0] or 0

    conn.close()

    login_flag = request.args.get("login", "0")

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

        <style>
            body { background: #fafafa; }
            .card { border-radius: 15px; }
            .btn-main { background: #ff4da6; color: white; }
            .toast-container {
                position: fixed;
                top: 1rem;
                right: 1rem;
                z-index: 9999;
            }
        </style>
    </head>

    <body>

    <div class="toast-container">
      <div id="visitToast" class="toast align-items-center text-bg-dark border-0" role="alert">
        <div class="d-flex">
          <div class="toast-body">
            New visit recorded.
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>

      <div id="welcomeToast" class="toast align-items-center text-bg-primary border-0" role="alert">
        <div class="d-flex">
          <div class="toast-body">
            Welcome Network Manager.
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>
    </div>

    """ + NAVBAR + """
    <div class="container mt-4">

        <div class="row">
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h5>Total Orders</h5>
                    <h2>{{ total_orders }}</h2>
                </div>
            </div>
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h5>Total Profit</h5>
                    <h2>£{{ "%.2f" % total_profit }}</h2>
                </div>
            </div>
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h5>Stock Items</h5>
                    <h2>{{ stock_count }}</h2>
                </div>
            </div>
        </div>

        <div class="card p-3 shadow-sm mb-3">
            <h5>Profit Overview</h5>
            <canvas id="profitChart" height="120"></canvas>
        </div>

    </div>

    <script>
    document.addEventListener("DOMContentLoaded", function() {
        var visitToastEl = document.getElementById('visitToast');
        var visitToast = new bootstrap.Toast(visitToastEl);
        visitToast.show();

        var loginFlag = "{{ login_flag }}";
        if (loginFlag === "1") {
            var welcomeToastEl = document.getElementById('welcomeToast');
            var welcomeToast = new bootstrap.Toast(welcomeToastEl);
            welcomeToast.show();
        }

        fetch("/api/profit-data")
          .then(r => r.json())
          .then(data => {
              var ctx = document.getElementById('profitChart').getContext('2d');
              new Chart(ctx, {
                  type: 'line',
                  data: {
                      labels: data.labels,
                      datasets: [{
                          label: 'Profit (£)',
                          data: data.values,
                          borderColor: '#ff4da6',
                          backgroundColor: 'rgba(255,77,166,0.15)',
                          tension: 0.3,
                          fill: true
                      }]
                  },
                  options: {
                      plugins: { legend: { display: false } },
                      scales: {
                          x: { title: { display: true, text: 'Date' } },
                          y: { title: { display: true, text: 'Profit (£)' } }
                      }
                  }
              });
          });
    });
    </script>

    </body>
    </html>
    """
    return render_template_string(template,
                                  title="Dashboard",
                                  total_orders=total_orders,
                                  total_profit=total_profit,
                                  stock_count=stock_count,
                                  login_flag=login_flag)

# -----------------------------
# ORDERS
# -----------------------------
@app.route("/orders", methods=["GET", "POST"])
def orders():
    if not require_login():
        return redirect("/")

    log_event("Orders page opened")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
        whatnot_username = request.form.get("whatnot_username")
        order_code = request.form.get("order_code")
        date = request.form.get("date")
        buy_amount = float(request.form.get("buy_amount") or 0)
        sell_amount = float(request.form.get("sell_amount") or 0)
        status = "Pending"  # default

        c.execute("""
            INSERT INTO orders (whatnot_username, order_code, date, buy_amount, sell_amount, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (whatnot_username, order_code, date, buy_amount, sell_amount, status))
        conn.commit()

    c.execute("SELECT id, whatnot_username, order_code, date, buy_amount, sell_amount, status FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

        <style>
            body { background: #fafafa; }
            .card { border-radius: 15px; }
            .btn-main { background: #ff4da6; color: white; }
            .status-pill {
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.8rem;
            }
        </style>
    </head>

    <body>

    """ + NAVBAR + """
    <div class="container mt-4">

        <div class="card p-3 shadow-sm mb-3">
            <h5>Add Order</h5>
            <form method="POST" class="row g-2">
                <div class="col-12 col-md-4">
                    <label class="form-label">Whatnot Username</label>
                    <input name="whatnot_username" class="form-control" required>
                </div>
                <div class="col-12 col-md-4">
                    <label class="form-label">Order ID</label>
                    <input name="order_code" class="form-control" required>
                </div>
                <div class="col-12 col-md-4">
                    <label class="form-label">Date</label>
                    <input name="date" type="date" class="form-control" required>
                </div>
                <div class="col-6 col-md-3">
                    <label class="form-label">Amount Bought (£)</label>
                    <input name="buy_amount" type="number" step="0.01" class="form-control" required>
                </div>
                <div class="col-6 col-md-3">
                    <label class="form-label">Amount Sold (£)</label>
                    <input name="sell_amount" type="number" step="0.01" class="form-control" required>
                </div>
                <div class="col-12 col-md-3 d-flex align-items-end">
                    <button class="btn btn-main w-100" type="submit">Add Order</button>
                </div>
            </form>
        </div>

        <div class="card p-3 shadow-sm">
            <h5>Orders</h5>
            <div class="table-responsive mt-2">
                <table class="table table-sm align-middle">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Whatnot Username</th>
                            <th>Order ID</th>
                            <th>Date</th>
                            <th>Buy (£)</th>
                            <th>Sell (£)</th>
                            <th>Profit (£)</th>
                            <th>Status</th>
                            <th>Change Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr>
                            <td>{{ o.id }}</td>
                            <td>{{ o.whatnot_username }}</td>
                            <td>{{ o.order_code }}</td>
                            <td>{{ o.date }}</td>
                            <td>£{{ "%.2f" % o.buy_amount }}</td>
                            <td>£{{ "%.2f" % o.sell_amount }}</td>
                            <td>£{{ "%.2f" % (o.sell_amount - o.buy_amount) }}</td>
                            <td>
                                <span class="status-pill
                                    {% if o.status == 'Completed' %}bg-success text-white
                                    {% elif o.status == 'Shipped' %}bg-info text-white
                                    {% elif o.status == 'Cancelled' %}bg-danger text-white
                                    {% else %}bg-secondary text-white{% endif %}">
                                    {{ o.status }}
                                </span>
                            </td>
                            <td>
                                <form method="POST" action="/orders/update/{{ o.id }}" class="d-flex gap-1">
                                    <select name="status" class="form-select form-select-sm">
                                        <option {% if o.status=='Pending' %}selected{% endif %}>Pending</option>
                                        <option {% if o.status=='Shipped' %}selected{% endif %}>Shipped</option>
                                        <option {% if o.status=='Completed' %}selected{% endif %}>Completed</option>
                                        <option {% if o.status=='Cancelled' %}selected{% endif %}>Cancelled</option>
                                    </select>
                                    <button class="btn btn-sm btn-outline-primary" type="submit">Save</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    </body>
    </html>
    """

    orders = []
    for r in rows:
        orders.append({
            "id": r[0],
            "whatnot_username": r[1],
            "order_code": r[2],
            "date": r[3],
            "buy_amount": r[4],
            "sell_amount": r[5],
            "status": r[6]
        })

    return render_template_string(template, title="Orders", orders=orders)

@app.route("/orders/update/<int:order_id>", methods=["POST"])
def update_order(order_id):
    if not require_login():
        return redirect("/")

    status = request.form.get("status")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    log_event(f"Order {order_id} status changed to {status}")
    return redirect("/orders")

# -----------------------------
# STOCKS
# -----------------------------
@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    if not require_login():
        return redirect("/")

    log_event("Stocks page opened")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
        item_name = request.form.get("item_name")
        quantity = int(request.form.get("quantity") or 0)
        buy_price = float(request.form.get("buy_price") or 0)
        notes = request.form.get("notes")

        c.execute("""
            INSERT INTO stocks (item_name, quantity, buy_price, notes)
            VALUES (?, ?, ?, ?)
        """, (item_name, quantity, buy_price, notes))
        conn.commit()

    c.execute("SELECT id, item_name, quantity, buy_price, notes FROM stocks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

        <style>
            body { background: #fafafa; }
            .card { border-radius: 15px; }
            .btn-main { background: #ff4da6; color: white; }
        </style>
    </head>

    <body>

    """ + NAVBAR + """
    <div class="container mt-4">

        <div class="card p-3 shadow-sm mb-3">
            <h5>Add Stock Item</h5>
            <form method="POST" class="row g-2">
                <div class="col-12 col-md-4">
                    <label class="form-label">Item Name</label>
                    <input name="item_name" class="form-control" required>
                </div>
                <div class="col-6 col-md-2">
                    <label class="form-label">Quantity</label>
                    <input name="quantity" type="number" class="form-control" required>
                </div>
                <div class="col-6 col-md-3">
                    <label class="form-label">Buy Price (£)</label>
                    <input name="buy_price" type="number" step="0.01" class="form-control" required>
                </div>
                <div class="col-12 col-md-3">
                    <label class="form-label">Notes</label>
                    <input name="notes" class="form-control">
                </div>
                <div class="col-12 d-flex justify-content-end">
                    <button class="btn btn-main" type="submit">Add Stock</button>
                </div>
            </form>
        </div>

        <div class="card p-3 shadow-sm">
            <h5>Current Stock</h5>
            <div class="table-responsive mt-2">
                <table class="table table-sm align-middle">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Item</th>
                            <th>Quantity</th>
                            <th>Buy Price (£)</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for s in stocks %}
                        <tr>
                            <td>{{ s.id }}</td>
                            <td>{{ s.item_name }}</td>
                            <td>{{ s.quantity }}</td>
                            <td>£{{ "%.2f" % s.buy_price }}</td>
                            <td>{{ s.notes }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    </body>
    </html>
    """

    stocks = []
    for r in rows:
        stocks.append({
            "id": r[0],
            "item_name": r[1],
            "quantity": r[2],
            "buy_price": r[3],
            "notes": r[4]
        })

    return render_template_string(template, title="Stocks", stocks=stocks)

# -----------------------------
# PROFIT PAGE (GRAPH)
# -----------------------------
@app.route("/profit")
def profit():
    if not require_login():
        return redirect("/")

    log_event("Profit page opened")

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

        <style>
            body { background: #fafafa; }
            .card { border-radius: 15px; }
        </style>
    </head>

    <body>

    """ + NAVBAR + """
    <div class="container mt-4">
        <div class="card p-3 shadow-sm mb-3">
            <h5>Profit Over Time</h5>
            <canvas id="profitChart" height="140"></canvas>
        </div>
    </div>

    <script>
    document.addEventListener("DOMContentLoaded", function() {
        fetch("/api/profit-data")
          .then(r => r.json())
          .then(data => {
              var ctx = document.getElementById('profitChart').getContext('2d');
              new Chart(ctx, {
                  type: 'line',
                  data: {
                      labels: data.labels,
                      datasets: [{
                          label: 'Profit (£)',
                          data: data.values,
                          borderColor: '#ff4da6',
                          backgroundColor: 'rgba(255,77,166,0.15)',
                          tension: 0.3,
                          fill: true
                      }]
                  },
                  options: {
                      plugins: { legend: { display: false } },
                      scales: {
                          x: { title: { display: true, text: 'Date' } },
                          y: { title: { display: true, text: 'Profit (£)' } }
                      }
                  }
              });
          });
    });
    </script>

    </body>
    </html>
    """
    return render_template_string(template, title="Profit")

@app.route("/api/profit-data")
def profit_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT date, SUM(sell_amount - buy_amount) as profit
        FROM orders
        GROUP BY date
        ORDER BY date
    """)
    rows = c.fetchall()
    conn.close()

    labels = [r[0] for r in rows]
    values = [round(r[1] or 0, 2) for r in rows]

    return jsonify({"labels": labels, "values": values})

# -----------------------------
# ADMIN PANEL (FOR YOU)
# -----------------------------
@app.route("/admin")
def admin_panel():
    if not require_login():
        return redirect("/")

    log_event("Admin panel opened")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM visits")
    total_visits = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM stocks")
    total_stocks = c.fetchone()[0] or 0

    c.execute("SELECT id, event, timestamp FROM visits ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()

    conn.close()

    template = """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>

        <style>
            body { background: #fafafa; }
            .card { border-radius: 15px; }
        </style>
    </head>

    <body>

    """ + NAVBAR + """
    <div class="container mt-4">

        <div class="row mb-3">
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h6>Total Visits</h6>
                    <h3>{{ total_visits }}</h3>
                </div>
            </div>
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h6>Total Orders</h6>
                    <h3>{{ total_orders }}</h3>
                </div>
            </div>
            <div class="col-12 col-md-4 mb-3">
                <div class="card p-3 shadow-sm">
                    <h6>Total Stock Items</h6>
                    <h3>{{ total_stocks }}</h3>
                </div>
            </div>
        </div>

        <div class="card p-3 shadow-sm">
            <h5>Recent Activity</h5>
            <div class="table-responsive mt-2">
                <table class="table table-sm align-middle">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Event</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for v in visits %}
                        <tr>
                            <td>{{ v.id }}</td>
                            <td>{{ v.event }}</td>
                            <td>{{ v.timestamp }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    </body>
    </html>
    """

    visits = []
    for r in rows:
        visits.append({"id": r[0], "event": r[1], "timestamp": r[2]})

    return render_template_string(template,
                                  title="Admin Panel",
                                  total_visits=total_visits,
                                  total_orders=total_orders,
                                  total_stocks=total_stocks,
                                  visits=visits)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
