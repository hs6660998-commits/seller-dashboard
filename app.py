from flask import Flask, request, redirect, session, url_for
import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secure_key_123"

DATA_FILE = "seller_data.json"
LOG_DB = "activity_logs.db"
WHATNOT_FEE = 0.11

# ---------------- MULTI-USER LOGIN ----------------
USERS = {
    "admin": {
        "password": "admin",
        "display": "Network Manager",
        "role": "admin"
    },
    "wonders": {
        "password": "wonders",
        "display": "Gem",
        "role": "user"
    }
}

# ---------------- ACTIVITY LOGS (SQLite) ----------------

def init_log_db():
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# IMPORTANT: Run DB init at import time so Render creates the table
init_log_db()

def log_action(user, action):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, user, action) VALUES (?, ?, ?)", (ts, user, action))
    conn.commit()
    conn.close()

def get_logs(limit=200):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("SELECT timestamp, user, action FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------- DECORATORS (FIXED WITH @wraps) ----------------

def login_required(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapped_function

def admin_required(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return redirect(url_for("dashboard"))
        return func(*args, **kwargs)
    return wrapped_function

# ---------------- DATA ----------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"orders": [], "expenses": [], "inventory": [], "order_id": 1, "goal": 1000}

    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except:
            return {"orders": [], "expenses": [], "inventory": [], "order_id": 1, "goal": 1000}

    defaults = {"orders": [], "expenses": [], "inventory": [], "order_id": 1, "goal": 1000}
    for key, value in defaults.items():
        if key not in data:
            data[key] = value

    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- HTML WRAPPER (MOBILE FRIENDLY) ----------------

def page(title, content, back_url="/dashboard", notification=None):
    logged_in = session.get("logged_in", False)

    notif_html = f"<div class='notif'>{notification}</div>" if notification else ""

    admin_link = "<a href='/admin'>Admin</a>" if logged_in and session.get("role") == "admin" else ""

    navbar = ""
    if logged_in:
        navbar = f"""
        <div class="navbar">
            {title}
            <div class="hamburger" onclick="toggleMenu()">☰</div>

            <div class="tabs">
                <a href="/dashboard">Dashboard</a>
                <a href="/orders">Orders</a>
                <a href="/inventory">Inventory</a>
                <a href="/expenses">Expenses</a>
                <a href="/analytics">Analytics</a>
                {admin_link}
                <a href="/logout">Logout</a>
            </div>

            <div id="mobileMenu" class="mobile-menu">
                <a href="/dashboard">Dashboard</a>
                <a href="/orders">Orders</a>
                <a href="/inventory">Inventory</a>
                <a href="/expenses">Expenses</a>
                <a href="/analytics">Analytics</a>
                {admin_link}
                <a href="/logout">Logout</a>
            </div>
        </div>
        """

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <style>
            body {{
                background:#fff0f6;
                font-family:Arial, sans-serif;
                margin:0;
                padding:0;
            }}

            .container {{
                width:95%;
                max-width:900px;
                margin:30px auto;
                background:white;
                padding:25px;
                border-radius:12px;
                box-shadow:0 4px 10px rgba(0,0,0,0.1);
            }}

            .navbar {{
                background:#ff4da6;
                padding:15px;
                text-align:center;
                color:white;
                font-size:20px;
                font-weight:bold;
                position:relative;
            }}

            .tabs a {{
                color:white;
                margin:0 12px;
                text-decoration:none;
                font-size:16px;
            }}

            .hamburger {{
                display:none;
                position:absolute;
                right:15px;
                top:15px;
                font-size:26px;
                cursor:pointer;
            }}

            .mobile-menu {{
                display:none;
                flex-direction:column;
                background:#ff4da6;
                padding:10px;
            }}

            .mobile-menu a {{
                color:white;
                padding:10px;
                text-decoration:none;
                border-bottom:1px solid rgba(255,255,255,0.3);
            }}

            .card {{
                background:#fff0f6;
                padding:15px;
                margin:10px 0;
                border-radius:10px;
            }}

            input {{
                width:100%;
                padding:12px;
                margin:10px 0;
                border-radius:6px;
                border:1px solid #ccc;
            }}

            .btn {{
                background:#ff4da6;
                color:white;
                padding:12px 20px;
                border-radius:6px;
                text-decoration:none;
                display:inline-block;
                margin-top:10px;
            }}

            table {{
                width:100%;
                border-collapse:collapse;
            }}

            th, td {{
                padding:10px;
                border-bottom:1px solid #eee;
            }}

            canvas {{
                width:100% !important;
                height:auto !important;
            }}

            @media (max-width:700px) {{
                .tabs {{ display:none; }}
                .hamburger {{ display:block; }}
                .container {{ padding:15px; }}
            }}
        </style>
    </head>

    <body>

        {notif_html}
        {navbar}

        <div class="container">
            {content}
            {"<a href='" + back_url + "' class='btn'>⬅ Back</a>" if logged_in else ""}
        </div>

        <script>
        function toggleMenu() {{
            const menu = document.getElementById("mobileMenu");
            menu.style.display = (menu.style.display === "flex") ? "none" : "flex";
        }}
        </script>

    </body>
    </html>
    """

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect("/dashboard")

    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username]["password"] == password:
            session["logged_in"] = True
            session["username"] = username
            session["display"] = USERS[username]["display"]
            session["role"] = USERS[username]["role"]
            log_action(session["display"], "Logged in")
            return redirect("/dashboard")
        else:
            error = "<p style='color:red;'>Incorrect login</p>"

    return page("Login", f"""
        <h2>Login</h2>
        {error}
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button class='btn'>Login</button>
        </form>
    """, back_url=None)

@app.route("/logout")
def logout():
    if session.get("logged_in"):
        log_action(session.get("display"), "Logged out")
    session.clear()
    return redirect("/")

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    data = load_data()

    revenue = sum(float(o["sale_price"]) for o in data["orders"])
    costs = sum(float(o["item_cost"]) for o in data["orders"])
    shipping = sum(float(o["shipping"]) for o in data["orders"])
    fees = revenue * WHATNOT_FEE
    expenses = sum(float(e["amount"]) for e in data["expenses"])
    profit = revenue - fees - shipping - costs - expenses

    goal = data["goal"]
    progress = (revenue / goal) * 100 if goal > 0 else 0

    return page("Dashboard", f"""
        <h2>Overview</h2>

        <p><b>Total Orders:</b> {len(data['orders'])}</p>
        <p><b>Total Revenue:</b> £{revenue:.2f}</p>
        <p><b>Total Profit:</b> £{profit:.2f}</p>
        <p><b>Total Expenses:</b> £{expenses:.2f}</p>

        <p><b>Goal:</b> £{goal} ({progress:.2f}%)</p>

        <div style='background:#ffe6f2; height:12px; border-radius:6px;'>
            <div style='background:#ff4da6; width:{progress}%; height:12px; border-radius:6px;'></div>
        </div>
    """)

# ---------------- INVENTORY ----------------

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    data = load_data()

    if request.method == "POST":
        name = request.form.get("name")
        stock = int(request.form.get("stock"))
        data["inventory"].append({"name": name, "stock": stock})
        save_data(data)
        log_action(session.get("display"), f"Added inventory item: {name}")
        return redirect("/inventory")

    items_html = "".join(
        f"<div class='card'><b>{i['name']}</b>: {i['stock']} in stock</div>"
        for i in data["inventory"]
    )

    return page("Inventory", f"""
        <h2>Add Item</h2>

        <form method='POST'>
            <input name='name' placeholder='Item Name' required>
            <input name='stock' placeholder='Stock Quantity' required>
            <button class='btn'>Add Item</button>
        </form>

        <h2>Inventory List</h2>
        {items_html}
    """)

# ---------------- ORDERS ----------------

@app.route("/orders", methods=["GET", "POST"])
@login_required
def orders():
    data = load_data()
    notification = None

    if request.method == "POST":
        item_name = request.form.get("item")
        sale_price = float(request.form.get("sale_price"))
        item_cost = float(request.form.get("item_cost"))
        shipping = float(request.form.get("shipping"))
        customer = request.form.get("customer")

        fee = sale_price * WHATNOT_FEE
        profit = sale_price - fee - shipping - item_cost

        new_order = {
            "id": data["order_id"],
            "item": item_name,
            "sale_price": sale_price,
            "item_cost": item_cost,
            "shipping": shipping,
            "customer": customer,
            "profit": profit,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        data["orders"].append(new_order)
        data["order_id"] += 1

        for item in data["inventory"]:
            if item["name"] == item_name:
                item["stock"] = max(0, item["stock"] - 1)

        save_data(data)
        log_action(session.get("display"), f"Added order: {item_name} (£{sale_price})")
        notification = f"New order added: <b>{item_name}</b> (£{sale_price})"

    orders_html = "".join(
        f"<div class='card'><b>Order #{o['id']}</b><br>Item: {o['item']}<br>Sale: £{o['sale_price']:.2f}<br>Profit: £{o['profit']:.2f}</div>"
        for o in data["orders"]
    )

    return page("Orders", f"""
        <h2>Add Order</h2>

        <form method='POST'>
            <input name='item' placeholder='Item Name' required>
            <input name='sale_price' placeholder='Sale Price' required>
            <input name='item_cost' placeholder='Item Cost' required>
            <input name='shipping' placeholder='Shipping Cost' required>
            <input name='customer' placeholder='Customer Name' required>
            <button class='btn'>Add Order</button>
        </form>

        <h2>Order List</h2>
        {orders_html}
    """, notification=notification)

# ---------------- EXPENSES ----------------

@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    data = load_data()

    if request.method == "POST":
        name = request.form.get("name")
        amount = float(request.form.get("amount"))
        data["expenses"].append({"name": name, "amount": amount})
        save_data(data)
        log_action(session.get("display"), f"Added expense: {name} (£{amount})")
        return redirect("/expenses")

    expenses_html = "".join(
        f"<div class='card'><b>{e['name']}</b>: £{e['amount']}</div>"
        for e in data["expenses"]
    )

    return page("Expenses", f"""
        <h2>Add Expense</h2>

        <form method='POST'>
            <input name='name' placeholder='Expense Name' required>
            <input name='amount' placeholder='Amount' required>
            <button class='btn'>Add Expense</button>
        </form>

        <h2>Expense List</h2>
        {expenses_html}
    """)

# ---------------- ANALYTICS ----------------

@app.route("/analytics")
@login_required
def analytics():
    data = load_data()

    monthly = {}
    for o in data["orders"]:
        month = o["date"][:7]
        monthly[month] = monthly.get(month, 0) + float(o["sale_price"])

    labels = list(monthly.keys())
    values = list(monthly.values())

    chart_js = f"""
        <canvas id="revenueChart"></canvas>

        <script>
            new Chart(document.getElementById('revenueChart'), {{
                type: 'line',
                data: {{
                    labels: {labels},
                    datasets: [{{
                        label: 'Monthly Revenue (£)',
                        data: {values},
                        borderColor: '#ff4da6',
                        backgroundColor: 'rgba(255, 77, 166, 0.2)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false
                }}
            }});
        </script>
    """

    return page("Analytics", f"""
        <h2>Monthly Revenue</h2>
        {chart_js}
    """)

# ---------------- ADMIN PANEL ----------------

@app.route("/admin")
@admin_required
def admin_home():
    data = load_data()

    content = f"""
        <h2>Admin Overview</h2>

        <p><b>Total Users:</b> {len(USERS)}</p>
        <p><b>Total Orders:</b> {len(data['orders'])}</p>
        <p><b>Total Inventory Items:</b> {len(data['inventory'])}</p>
        <p><b>Total Expenses:</b> {len(data['expenses'])}</p>

        <h3>Users</h3>
        <table>
            <tr><th>Username</th><th>Name</th><th>Role</th></tr>
            {''.join(f"<tr><td>{u}</td><td>{info['display']}</td><td>{info['role']}</td></tr>" for u, info in USERS.items())}
        </table>
    """

    return page("Admin Panel", content, back_url=None)

@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs = get_logs()

    rows = "".join(
        f"<tr><td>{ts}</td><td>{user}</td><td>{action}</td></tr>"
        for ts, user, action in logs
    )

    return page("Activity Logs", f"""
        <h2>Activity Logs</h2>
        <table>
            <tr><th>Timestamp</th><th>User</th><th>Action</th></tr>
            {rows}
        </table>
    """)

# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
