from flask import Flask, request, redirect, session, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secure_key_123"

DATA_FILE = "seller_data.json"
WHATNOT_FEE = 0.11

USERNAME = "admin"
PASSWORD = "admin"

PINK_MAIN = "#ff4da6"
PINK_LIGHT = "#fff0f6"


# ---------------- LOGIN REQUIRED ----------------

def login_required(func):
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorated_function


# ---------------- DATA ----------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "orders": [],
        "expenses": [],
        "inventory": [],
        "order_id": 1,
        "goal": 1000
    }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect("/dashboard")

    error = ""
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect("/dashboard")
        else:
            error = "Incorrect login"

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; text-align: center; font-family: Arial, sans-serif;">
                <h2>Login</h2>
                {f'<p style="color:red;">{error}</p>' if error else ''}
                <form method="POST">
                    <input name="username" placeholder="Username" required><br><br>
                    <input name="password" type="password" placeholder="Password" required><br><br>
                    <button style="background-color:{PINK_MAIN}; color:white; padding:10px 20px; border:none; border-radius:5px;">Login</button>
                </form>
            </body>
        </html>
    """


@app.route("/logout")
def logout():
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

    goal = data.get("goal", 1000)
    progress = (revenue / goal) * 100 if goal > 0 else 0

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; font-family: Arial, sans-serif; text-align: center;">
                <h2>Dashboard</h2>
                <p><strong>Total Orders:</strong> {len(data['orders'])}</p>
                <p><strong>Total Revenue:</strong> ${revenue:.2f}</p>
                <p><strong>Total Profit:</strong> ${profit:.2f}</p>
                <p><strong>Total Expenses:</strong> ${expenses:.2f}</p>
                <p><strong>Goal:</strong> ${goal} ({progress:.2f}% complete)</p>
                <div style="background-color: {PINK_MAIN}; height: 10px; width: {progress}%; margin: 10px auto;"></div>
                <a href="/orders" style="text-decoration: none; background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border-radius: 5px; margin: 5px;">Manage Orders</a><br>
                <a href="/expenses" style="text-decoration: none; background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border-radius: 5px; margin: 5px;">Manage Expenses</a><br>
                <a href="/inventory" style="text-decoration: none; background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border-radius: 5px; margin: 5px;">Manage Inventory</a><br>
                <a href="/analytics" style="text-decoration: none; background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border-radius: 5px; margin: 5px;">View Analytics</a><br>
            </body>
        </html>
    """


# ---------------- INVENTORY ----------------

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    data = load_data()

    if request.method == "POST":
        new_item = {
            "name": request.form.get("name"),
            "stock": int(request.form.get("stock"))
        }
        data["inventory"].append(new_item)
        save_data(data)
        return redirect("/inventory")

    inventory_list = ""
    for item in data["inventory"]:
        inventory_list += f"<div style='background-color: white; padding: 15px; margin: 10px; border-radius: 8px; box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);'><b>{item['name']}:</b> {item['stock']} in stock</div>"

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; font-family: Arial, sans-serif; text-align: center;">
                <h2>Inventory</h2>
                <form method="POST">
                    <input name="name" placeholder="Item Name" required><br><br>
                    <input name="stock" placeholder="Stock Quantity" required><br><br>
                    <button style="background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border: none; border-radius: 5px;">Add Item</button>
                </form>
                <h3>Inventory List</h3>
                {inventory_list}
            </body>
        </html>
    """


# ---------------- ORDERS ----------------

@app.route("/orders", methods=["GET", "POST"])
@login_required
def orders():
    data = load_data()

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
            "fee": fee,
            "profit": profit,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        data["orders"].append(new_order)
        data["order_id"] += 1

        for item in data["inventory"]:
            if item["name"] == item_name and item["stock"] > 0:
                item["stock"] -= 1

        save_data(data)
        return redirect("/orders")

    order_list = ""
    for o in data["orders"]:
        order_list += f"<div style='background-color: white; padding: 15px; margin: 10px; border-radius: 8px; box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);'><b>Order #{o['id']}</b><br><b>Item:</b> {o['item']}<br><b>Sale Price:</b> ${o['sale_price']:.2f}<br><b>Profit:</b> ${o['profit']:.2f}</div>"

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; font-family: Arial, sans-serif; text-align: center;">
                <h2>Orders</h2>
                <form method="POST">
                    <input name="item" placeholder="Item Name" required><br><br>
                    <input name="sale_price" placeholder="Sale Price" required><br><br>
                    <input name="item_cost" placeholder="Item Cost" required><br><br>
                    <input name="shipping" placeholder="Shipping Cost" required><br><br>
                    <input name="customer" placeholder="Customer Name" required><br><br>
                    <button style="background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border: none; border-radius: 5px;">Add Order</button>
                </form>
                <h3>Order List</h3>
                {order_list}
            </body>
        </html>
    """


# ---------------- EXPENSES ----------------

@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    data = load_data()

    if request.method == "POST":
        new_expense = {
            "name": request.form.get("name"),
            "amount": float(request.form.get("amount")),
            "category": request.form.get("category")
        }
        data["expenses"].append(new_expense)
        save_data(data)
        return redirect("/expenses")

    expense_list = ""
    for e in data["expenses"]:
        expense_list += f"<div style='background-color: white; padding: 15px; margin: 10px; border-radius: 8px; box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);'><b>{e['name']}:</b> ${e['amount']} (Category: {e['category']})</div>"

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; font-family: Arial, sans-serif; text-align: center;">
                <h2>Expenses</h2>
                <form method="POST">
                    <input name="name" placeholder="Expense Name" required><br><br>
                    <input name="amount" placeholder="Amount" required><br><br>
                    <input name="category" placeholder="Category" required><br><br>
                    <button style="background-color: {PINK_MAIN}; color: white; padding: 10px 20px; border: none; border-radius: 5px;">Add Expense</button>
                </form>
                <h3>Expenses List</h3>
                {expense_list}
            </body>
        </html>
    """


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

    return f"""
        <html>
            <body style="background: {PINK_LIGHT}; font-family: Arial, sans-serif; text-align: center;">
                <h2>Analytics - Monthly Revenue 📊</h2>
                <canvas id="chart" style="max-width: 600px; margin: 0 auto;"></canvas>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script>
                    const ctx = document.getElementById('chart').getContext('2d');
                    new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {labels},
                            datasets: [{{
                                label: 'Revenue',
                                data: {values},
                                backgroundColor: '{PINK_MAIN}'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{
                                    display: false
                                }}
                            }}
                        }}
                    }});
                </script>
            </body>
        </html>
    """


if __name__ == "__main__":
    app.run(debug=True)
