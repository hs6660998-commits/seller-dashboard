```python
import os, json
from time import time
from datetime import datetime, timedelta
from collections import Counter
from flask import (
    Flask, request, redirect, url_for, session,
    send_from_directory, flash, render_template_string
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "APIGem12")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

# Admin credentials (can be overridden via environment variables)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS")  # optional plain-text fallback
ADMIN_PASS_HASH = os.getenv("ADMIN_PASS_HASH")  # preferred: hashed password

# Simple in-memory login rate limiting
login_attempts = {}

def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def data_path(name):
    return os.path.join(DATA_DIR, name)

def load_json(name, default):
    p = data_path(name)
    if not os.path.exists(p):
        save_json(name, default)
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(name, data):
    with open(data_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

DEFAULT_HOMEPAGE = {
    "title": "Gemzy's Wardrobe Wonders",
    "tagline": "Fashion • Media • Style • Live Shows",
    "cta_text": "Watch Live",
    "cta_link": "https://www.whatnot.com/user/gemzyswardrobewonders",
    "hero_image": "media-relations.png",
    "background": "pink"
}
DEFAULT_FEATURED = []
DEFAULT_BANNER = {"enabled": False, "text": "", "color": "#ff69b4", "image": ""}
DEFAULT_ABOUT = {
    "heading": "About Gemzy",
    "text": "Gemzy brings curated fashion, live energy, and media magic to every show.",
    "image": ""
}
DEFAULT_SOCIALS = {
    "whatnot": "",
    "tiktok": "",
    "instagram": "",
    "depop": "",
    "email": "",
    "custom_label": "",
    "custom_link": ""
}
DEFAULT_NOTES = []
DEFAULT_STATS = {"views": 0}

def is_logged_in():
    return session.get("logged_in") is True

def require_login():
    if not is_logged_in():
        return redirect(url_for("admin_login"))

BASE_TEMPLATE = """
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><title>{{ title or "Gemzy" }}</title>
<style>
body{margin:0;font-family:Segoe UI,system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#ffb6c1,#ffe4e1);color:#333;}
a{text-decoration:none;}
.nav{background:#fff8fb;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 4px rgba(0,0,0,.05);}
.nav-left a{margin-right:15px;color:#ff1493;font-weight:600;}
.nav-right a{margin-left:10px;color:#555;font-size:.9rem;}
.container{max-width:1000px;margin:20px auto;padding:0 15px;}
.hero{padding:40px 20px;text-align:center;}
.hero-img{width:220px;margin-bottom:20px;}
h1{font-size:2.4rem;margin:10px 0;}
.tagline{font-size:1.1rem;margin-bottom:20px;}
.cta-button{display:inline-block;background:#ff69b4;color:#fff;padding:10px 22px;border-radius:30px;font-weight:600;}
.banner{padding:10px 15px;text-align:center;color:#fff;font-weight:600;}
.featured{padding:20px 0;}
.featured h2{margin-bottom:10px;}
.media-grid{display:flex;flex-wrap:wrap;gap:15px;justify-content:center;}
.media-item{background:#fff;padding:15px;border-radius:12px;box-shadow:0 3px 6px rgba(0,0,0,.08);width:220px;font-size:.9rem;}
.media-item img{max-width:100%;border-radius:8px;margin-bottom:8px;}
.socials{text-align:center;margin:30px 0;}
.socials a{margin:0 8px;color:#ff1493;font-weight:600;font-size:.95rem;}
.about{background:#fff8fb;border-radius:16px;padding:20px;margin:20px 0;display:flex;flex-wrap:wrap;gap:15px;align-items:center;}
.about-text{flex:2;min-width:200px;}
.about-img{flex:1;min-width:160px;text-align:center;}
.about-img img{max-width:100%;border-radius:12px;}
.admin-wrap{max-width:900px;margin:30px auto;padding:0 15px;}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 3px 6px rgba(0,0,0,.06);margin-bottom:20px;}
.card h2{margin-top:0;}
input[type=text],input[type=password],input[type=url],textarea,select{width:100%;padding:8px 10px;margin:6px 0 12px;border-radius:8px;border:1px solid #ddd;font-family:inherit;font-size:.95rem;}
textarea{min-height:80px;resize:vertical;}
button,.btn{display:inline-block;padding:8px 16px;border-radius:20px;border:none;background:#ff69b4;color:#fff;font-weight:600;cursor:pointer;font-size:.9rem;}
.btn-secondary{background:#eee;color:#444;}
.btn-danger{background:#ff4b6a;}
.error{color:#d00;font-size:.9rem;margin-bottom:8px;}
.flash{padding:8px 12px;border-radius:8px;margin-bottom:10px;font-size:.9rem;}
.flash-success{background:#e6ffef;color:#137333;}
.flash-error{background:#ffe6ea;color:#b00020;}
.login-box{max-width:320px;margin:80px auto;}
.login-box h2{text-align:center;margin-bottom:10px;}
.notes-list li{margin-bottom:6px;font-size:.9rem;}
.notes-list span.done{text-decoration:line-through;color:#777;}
.upload-list li{font-size:.9rem;margin-bottom:4px;}
.logs-table{width:100%;border-collapse:collapse;font-size:.85rem;}
.logs-table th,.logs-table td{border:1px solid #eee;padding:6px 8px;text-align:left;}
.logs-table th{background:#fff8fb;}
@media(max-width:700px){.about{flex-direction:column;}.hero-img{width:180px;}}
</style>
</head><body>
<div class="nav">
  <div class="nav-left">
    <a href="{{ url_for('homepage') }}">Home</a>
  </div>
  <div class="nav-right">
    {% if admin %}
      <a href="{{ url_for('dashboard') }}">Dashboard</a>
      <a href="{{ url_for('notes') }}">Notes</a>
      <a href="{{ url_for('uploads') }}">Uploads</a>
      <a href="{{ url_for('logs_view') }}">Logs</a>
      <a href="{{ url_for('logout') }}">Logout</a>
    {% else %}
      <a href="{{ url_for('admin_login') }}">Admin</a>
    {% endif %}
  </div>
</div>
<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat,msg in messages %}
        <div class="flash flash-{{cat}}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {{ body|safe }}
</div>
</body></html>
"""

HOMEPAGE_BODY = """
{% if banner.enabled %}
<div class="banner" style="background:{{ banner.color }};">
  {{ banner.text }}
</div>
{% endif %}
<div class="hero">
  <img src="{{ url_for('static', filename=homepage.hero_image) if not homepage.hero_image.startswith('uploads/') else url_for('uploaded_file', filename=homepage.hero_image.split('uploads/')[1]) }}" class="hero-img">
  <h1>{{ homepage.title }}</h1>
  <p class="tagline">{{ homepage.tagline }}</p>
  <a href="{{ homepage.cta_link }}" class="cta-button" target="_blank">{{ homepage.cta_text }}</a>
</div>
<div class="featured">
  <h2>Featured Media</h2>
  <div class="media-grid">
    {% for item in featured %}
      <div class="media-item">
        {% if item.image %}
          <img src="{{ url_for('uploaded_file', filename=item.image.split('uploads/')[1]) }}">
        {% endif %}
        {% if item.title %}<strong>{{ item.title }}</strong><br>{% endif %}
        {% if item.caption %}<span>{{ item.caption }}</span><br>{% endif %}
        {% if item.link %}<a href="{{ item.link }}" target="_blank">View</a>{% endif %}
      </div>
    {% else %}
      <p>No featured media yet.</p>
    {% endfor %}
  </div>
</div>
<div class="about">
  <div class="about-text">
    <h2>{{ about.heading }}</h2>
    <p>{{ about.text }}</p>
  </div>
  <div class="about-img">
    {% if about.image %}
      <img src="{{ url_for('uploaded_file', filename=about.image.split('uploads/')[1]) }}">
    {% endif %}
  </div>
</div>
<div class="socials">
  {% if socials.whatnot %}<a href="{{ socials.whatnot }}" target="_blank">Whatnot</a>{% endif %}
  {% if socials.tiktok %}<a href="{{ socials.tiktok }}" target="_blank">TikTok</a>{% endif %}
  {% if socials.instagram %}<a href="{{ socials.instagram }}" target="_blank">Instagram</a>{% endif %}
  {% if socials.depop %}<a href="{{ socials.depop }}" target="_blank">Depop</a>{% endif %}
  {% if socials.email %}<a href="mailto:{{ socials.email }}">Email</a>{% endif %}
  {% if socials.custom_link and socials.custom_label %}<a href="{{ socials.custom_link }}" target="_blank">{{ socials.custom_label }}</a>{% endif %}
</div>
"""

LOGIN_BODY = """
<div class="login-box card">
  <h2>Admin Login</h2>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post">
    <input type="text" name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <button type="submit">Login</button>
  </form>
</div>
"""

DASHBOARD_BODY = """
<div class="card">
  <h2>Dashboard</h2>
  <p><strong>Homepage title:</strong> {{ homepage.title }}</p>
  <p><strong>Total visits (logged):</strong> {{ total_visits }}</p>
  <p><strong>Unique visitors (by IP):</strong> {{ unique_ips }}</p>
  <p><strong>Homepage views:</strong> {{ stats.views }}</p>
  <p><strong>Live visitors (last 60s):</strong> {{ live_visitors }}</p>
  <p><strong>Notes:</strong> {{ notes|length }}</p>
  <p><strong>Uploaded files:</strong> {{ files_count }}</p>
</div>
<div class="card">
  <h3>Device breakdown</h3>
  {% if device_breakdown %}
    <ul>
      {% for label,count in device_breakdown %}
        <li>{{ label }}: {{ count }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No device data yet.</p>
  {% endif %}
</div>
<div class="card">
  <h3>Traffic sources</h3>
  {% if sources %}
    <ul>
      {% for label,count in sources %}
        <li>{{ label }}: {{ count }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No source data yet.</p>
  {% endif %}
</div>
"""

NOTES_BODY = """
<div class="card">
  <h2>Notes</h2>
  <form method="post">
    <label>New Note</label>
    <input type="text" name="text">
    <button type="submit">Add</button>
  </form>
</div>
<div class="card">
  <h3>All Notes</h3>
  <ul class="notes-list">
    {% for n in notes %}
      <li>
        <span class="{% if n.done %}done{% endif %}">{{ n.text }}</span>
        <form method="post" action="{{ url_for('toggle_note', note_id=n.id) }}" style="display:inline;">
          <button class="btn btn-secondary" type="submit">Toggle</button>
        </form>
        <form method="post" action="{{ url_for('delete_note', note_id=n.id) }}" style="display:inline;">
          <button class="btn btn-danger" type="submit">Delete</button>
        </form>
      </li>
    {% else %}
      <li>No notes yet.</li>
    {% endfor %}
  </ul>
</div>
"""

UPLOADS_BODY = """
<div class="card">
  <h2>Uploads</h2>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">Upload</button>
  </form>
</div>
<div class="card">
  <h3>Files</h3>
  <ul class="upload-list">
    {% for f in files %}
      <li>
        <a href="{{ url_for('uploaded_file', filename=f) }}" target="_blank">{{ f }}</a>
        <form method="post" action="{{ url_for('delete_upload', filename=f) }}" style="display:inline;">
          <button class="btn btn-danger" type="submit">Delete</button>
        </form>
      </li>
    {% else %}
      <li>No files uploaded yet.</li>
    {% endfor %}
  </ul>
</div>
"""

LOGS_BODY = """
<div class="card">
  <h2>Visitor Logs</h2>
  <p>Showing latest {{ logs|length }} entries.</p>
  <table class="logs-table">
    <tr>
      <th>Time (UTC)</th>
      <th>IP</th>
      <th>Path</th>
      <th>Source</th>
      <th>Device</th>
    </tr>
    {% for e in logs %}
      <tr>
        <td>{{ e.time }}</td>
        <td>{{ e.ip }}</td>
        <td>{{ e.path }}</td>
        <td>{{ e.source }}</td>
        <td>{{ e.device }}</td>
      </tr>
    {% else %}
      <tr><td colspan="5">No logs yet.</td></tr>
    {% endfor %}
  </table>
</div>
"""

def classify_device(agent: str) -> str:
    if not agent:
        return "Unknown"
    ua = agent.lower()
    if "iphone" in ua or "ipad" in ua:
        return "iOS"
    if "android" in ua:
        return "Android"
    if "windows" in ua:
        return "Windows"
    if "mac os" in ua or "macintosh" in ua:
        return "Mac"
    return "Other"

def source_label(referrer: str, src_param: str) -> str:
    if src_param:
        return src_param.lower()
    if not referrer:
        return "direct"
    ref = referrer.lower()
    if "instagram" in ref:
        return "instagram"
    if "tiktok" in ref:
        return "tiktok"
    if "whatnot" in ref:
        return "whatnot"
    if "depop" in ref:
        return "depop"
    return "other"

@app.before_request
def track_and_log():
    # homepage view counter
    if request.endpoint == "homepage":
        stats = load_json("stats.json", DEFAULT_STATS)
        stats["views"] = stats.get("views", 0) + 1
        save_json("stats.json", stats)

    # log all requests except static files
    if request.path.startswith("/static/"):
        return

    logs = load_json("logs.json", [])
    entry = {
        "ip": request.remote_addr or "unknown",
        "agent": request.headers.get("User-Agent", ""),
        "path": request.path,
        "time": datetime.utcnow().isoformat(),
        "ref": request.referrer,
        "src": request.args.get("src") or ""
    }
    logs.append(entry)
    # keep last 5000 entries
    if len(logs) > 5000:
        logs = logs[-5000:]
    save_json("logs.json", logs)

@app.route("/")
def homepage():
    homepage_data = load_json("homepage.json", DEFAULT_HOMEPAGE)
    featured = load_json("featured.json", DEFAULT_FEATURED)
    banner = load_json("banner.json", DEFAULT_BANNER)
    about = load_json("about.json", DEFAULT_ABOUT)
    socials = load_json("socials.json", DEFAULT_SOCIALS)
    body = render_template_string(
        HOMEPAGE_BODY,
        homepage=homepage_data,
        featured=featured,
        banner=banner,
        about=about,
        socials=socials
    )
    return render_template_string(
        BASE_TEMPLATE,
        title=homepage_data["title"],
        body=body,
        admin=is_logged_in()
    )

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

def too_many_attempts(ip):
    now = time()
    attempts = login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < 60]
    login_attempts[ip] = attempts
    return len(attempts) >= 5

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        ip = request.remote_addr or "unknown"

        if too_many_attempts(ip):
            error = "Too many attempts. Try again in a minute."
        else:
            login_attempts.setdefault(ip, []).append(time())

            if ADMIN_PASS_HASH:
                ok = (u == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, p))
            else:
                expected_pass = ADMIN_PASS or "admin"
                ok = (u == ADMIN_USER and p == expected_pass)

            if ok:
                session["logged_in"] = True
                return redirect(url_for("dashboard"))
            else:
                error = "Incorrect username or password."

    body = render_template_string(LOGIN_BODY, error=error)
    return render_template_string(
        BASE_TEMPLATE,
        title="Admin Login",
        body=body,
        admin=False
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/dashboard")
def dashboard():
    r = require_login()
    if r:
        return r

    homepage_data = load_json("homepage.json", DEFAULT_HOMEPAGE)
    notes = load_json("notes.json", DEFAULT_NOTES)
    stats = load_json("stats.json", DEFAULT_STATS)
    try:
        files = os.listdir(UPLOAD_DIR)
    except FileNotFoundError:
        files = []

    logs = load_json("logs.json", [])
    total_visits = len(logs)
    unique_ips = len({e.get("ip", "") for e in logs if e.get("ip")})

    # live visitors (last 60 seconds)
    live_cutoff = datetime.utcnow() - timedelta(seconds=60)
    live_visitors = 0
    for e in logs:
        try:
            t = datetime.fromisoformat(e.get("time", ""))
            if t >= live_cutoff:
                live_visitors += 1
        except Exception:
            continue

    # device breakdown
    device_counts = Counter()
    for e in logs:
        device_counts[classify_device(e.get("agent", ""))] += 1
    device_breakdown = list(device_counts.items())

    # traffic sources
    source_counts = Counter()
    for e in logs:
        src = source_label(e.get("ref", ""), e.get("src", ""))
        source_counts[src] += 1
    sources = list(source_counts.items())

    body = render_template_string(
        DASHBOARD_BODY,
        homepage=homepage_data,
        notes=notes,
        stats=stats,
        files_count=len(files),
        total_visits=total_visits,
        unique_ips=unique_ips,
        live_visitors=live_visitors,
        device_breakdown=device_breakdown,
        sources=sources
    )
    return render_template_string(
        BASE_TEMPLATE,
        title="Dashboard",
        body=body,
        admin=True
    )

@app.route("/admin/notes", methods=["GET", "POST"])
def notes():
    r = require_login()
    if r:
        return r
    notes_data = load_json("notes.json", DEFAULT_NOTES)
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            new_id = max([n["id"] for n in notes_data], default=0) + 1
            notes_data.append({"id": new_id, "text": text, "done": False})
            save_json("notes.json", notes_data)
            flash("Note added.", "success")
        return redirect(url_for("notes"))
    body = render_template_string(NOTES_BODY, notes=notes_data)
    return render_template_string(
        BASE_TEMPLATE,
        title="Notes",
        body=body,
        admin=True
    )

@app.route("/admin/notes/toggle/<int:note_id>", methods=["POST"])
def toggle_note(note_id):
    r = require_login()
    if r:
        return r
    notes_data = load_json("notes.json", DEFAULT_NOTES)
    for n in notes_data:
        if n["id"] == note_id:
            n["done"] = not n["done"]
            break
    save_json("notes.json", notes_data)
    return redirect(url_for("notes"))

@app.route("/admin/notes/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    r = require_login()
    if r:
        return r
    notes_data = load_json("notes.json", DEFAULT_NOTES)
    notes_data = [n for n in notes_data if n["id"] != note_id]
    save_json("notes.json", notes_data)
    flash("Note deleted.", "success")
    return redirect(url_for("notes"))

@app.route("/admin/uploads", methods=["GET", "POST"])
def uploads():
    r = require_login()
    if r:
        return r
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename and allowed_file(f.filename):
            fn = secure_filename(f.filename)
            f.save(os.path.join(UPLOAD_DIR, fn))
            flash("File uploaded.", "success")
        else:
            flash("Invalid file.", "error")
        return redirect(url_for("uploads"))
    try:
        files = os.listdir(UPLOAD_DIR)
    except FileNotFoundError:
        files = []
    body = render_template_string(UPLOADS_BODY, files=files)
    return render_template_string(
        BASE_TEMPLATE,
        title="Uploads",
        body=body,
        admin=True
    )

@app.route("/admin/uploads/delete/<filename>", methods=["POST"])
def delete_upload(filename):
    r = require_login()
    if r:
        return r
    p = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(p):
        os.remove(p)
        flash("File deleted.", "success")
    return redirect(url_for("uploads"))

@app.route("/admin/logs")
def logs_view():
    r = require_login()
    if r:
        return r
    raw_logs = load_json("logs.json", [])
    # show latest 200 entries
    latest = raw_logs[-200:]
    # map to simple objects for template
    logs = []
    for e in reversed(latest):
        logs.append(type("LogEntry", (), {
            "time": e.get("time", ""),
            "ip": e.get("ip", ""),
            "path": e.get("path", ""),
            "source": source_label(e.get("ref", ""), e.get("src", "")),
            "device": classify_device(e.get("agent", ""))
        }))
    body = render_template_string(LOGS_BODY, logs=logs)
    return render_template_string(
        BASE_TEMPLATE,
        title="Logs",
        body=body,
        admin=True
    )

if __name__ == "__main__":
    app.run(debug=True)
```
