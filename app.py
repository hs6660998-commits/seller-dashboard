from flask import Flask, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "APIadmin"

# -----------------------------
# DATABASE SETUP
# -----------------------------
def init_log_db():
    conn = sqlite3.connect("logs.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_action(action):
    conn = sqlite3.connect("logs.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs (action) VALUES (?)", (action,))
    conn.commit()
    conn.close()

init_log_db()

# -----------------------------
# PWA ROUTES
# -----------------------------
@app.route("/manifest.json")
def manifest():
    return {
        "name": "Seller Dashboard",
        "short_name": "Dashboard",
        "start_url": "/",
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
# LOGIN PAGE
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        # FIXED LOGIN — admin/admin ONLY
        if user == "admin" and pw == "admin":
            session["logged_in"] = True
            log_action("Admin logged in")
            return redirect("/dashboard")
        else:
            return """
            <script>alert('Invalid username or password');window.location='/'</script>
            """

    return """
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

# -----------------------------
# DASHBOARD PAGE
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/")

    return """
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
            body { background: #fafafa; }
            .navbar { background: #ff4da6 !important; }
            .card { border-radius: 15px; }
            .btn-main { background: #ff4da6; color: white; }
        </style>
    </head>

    <body>

    <nav class="navbar navbar-dark">
      <div class="container-fluid">
        <span class="navbar-brand">Seller Dashboard</span>
      </div>
    </nav>

    <div class="container mt-4">

        <div class="card p-3 shadow-sm mb-3">
            <h4>Welcome back, admin!</h4>
            <p>Your sales overview will appear here.</p>
        </div>

        <div class="card p-3 shadow-sm mb-3">
            <h5>Quick Actions</h5>
            <button class="btn btn-main mt-2">Add Product</button>
        </div>

    </div>

    </body>
    </html>
    """

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
