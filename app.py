from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "super-secret-key"

DB = "bank.db"

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount REAL,
        flagged INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    # default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?,?,1)",
            ("admin", generate_password_hash("admin123"))
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- ROUTES ----------------
@app@app.route("/", methods=["GET", "HEAD"])
def index():
    if request.method == "HEAD":
        return "", 200
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = generate_password_hash(request.form["password"])

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO users (username,password,balance) VALUES (?,?,1000)", (u,p))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            return "Username already exists"

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (u,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], p):
            session["user"] = u
            session["admin"] = user[4]
            return redirect("/dashboard")
        return "Invalid login"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=?", (session["user"],))
    balance = c.fetchone()[0]

    c.execute("SELECT * FROM transactions WHERE sender=? OR receiver=?",
              (session["user"], session["user"]))
    tx = c.fetchall()
    conn.close()

    return render_template("dashboard.html", balance=balance, tx=tx)

@app.route("/transfer", methods=["POST"])
def transfer():
    sender = session["user"]
    receiver = request.form["to"]
    amount = float(request.form["amount"])

    flagged = 1 if amount > 5000 else 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=?", (sender,))
    bal = c.fetchone()[0]

    if bal < amount:
        return "Insufficient funds"

    c.execute("UPDATE users SET balance=balance-? WHERE username=?", (amount,sender))
    c.execute("UPDATE users SET balance=balance+? WHERE username=?", (amount,receiver))
    c.execute("""INSERT INTO transactions 
        (sender,receiver,amount,flagged,created_at)
        VALUES (?,?,?,?,?)""",
        (sender,receiver,amount,flagged,str(datetime.now()))
    )

    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return "Unauthorized"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE flagged=1")
    tx = c.fetchall()
    conn.close()

    return render_template("admin.html", tx=tx)

@app.route("/statement")
def statement():
    user = session["user"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE sender=? OR receiver=?", (user,user))
    rows = c.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200,10,f"Statement for {user}",ln=True)

    for r in rows:
        pdf.cell(200,8,f"{r[1]} → {r[2]} | {r[3]} | FLAG:{r[4]}",ln=True)

    path = f"{user}_statement.pdf"
    pdf.output(path)
    return send_file(path, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
