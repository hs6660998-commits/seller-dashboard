from flask import Flask, request, redirect, render_template_string, session, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"

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
            {
                "src": "/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
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

        if user == "admin" and pw == "password":
            session["logged_in"] = True
            log_action("User logged in")
            return redirect("/dashboard")
        else:
            return "Invalid login"

    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#ff4da6">

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>
    </head>
    <body>
        <h2>Login</h2>
        <form method="POST">
            <input name="username" placeholder="Username"><br>
            <input name="password" type="password" placeholder="Password"><br>
            <button type="submit">Login</button>
        </form>
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

        <script>
        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("/service-worker.js");
        }
        </script>
    </head>
    <body>
        <h1>Seller Dashboard</h1>
        <p>Welcome!</p>
    </body>
    </html>
    """

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
