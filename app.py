from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, os, random
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

    # Users table with account numbers
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        account_number TEXT UNIQUE
    )
    """)

    # Transactions table with reference
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount REAL,
        flagged INTEGER DEFAULT 0,
        created_at TEXT,
        reference TEXT
    )
    """)

    # Default admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_account = str(random.randint(1000000000, 9999999999))
        c.execute(
            "INSERT INTO users (username, password, is_admin, account_number) VALUES (?,?,1,?)",
            ("admin", generate_password_hash("admin123"), admin_account)
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "HEAD"])
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = generate_password_hash(request.form["password"])
        account_number = str(random.randint(1000000000, 9999999999))

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username,password,balance,account_number) VALUES (?,?,1000,?)",
                (u,p,account_number)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Username already exists or account number collision"

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

@app@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT balance, account_number FROM users WHERE username=?", (session["user"],))
    balance, account_number = c.fetchone()

    c.execute("""
        SELECT * FROM transactions
        WHERE sender=? OR receiver=?
        ORDER BY id DESC
    """, (session["user"], session["user"]))
    tx = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        balance=balance,
        account_number=account_number,
        tx=tx
    )

@appimport random

@app.route("/transfer", methods=["POST"])
def transfer():
    if "user" not in session:
        return redirect("/login")

    sender = session["user"]
    receiver_account = request.form["to_account"]
    amount = float(request.form["amount"])

    flagged = 1 if amount > 5000 else 0
    reference = f"TX{random.randint(10000000,99999999)}"
    status = "PENDING"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Sender info
    c.execute("SELECT balance, account_number FROM users WHERE username=?", (sender,))
    sender_balance, sender_account = c.fetchone()

    if sender_balance < amount:
        conn.close()
        return "Insufficient funds"

    # Receiver lookup by ACCOUNT NUMBER
    c.execute("SELECT username FROM users WHERE account_number=?", (receiver_account,))
    receiver = c.fetchone()

    if not receiver:
        conn.close()
        return "Invalid receiver account number"

    receiver = receiver[0]

    # Insert transaction as PENDING
    c.execute("""
        INSERT INTO transactions
        (sender, receiver, amount, flagged, created_at, reference, status)
        VALUES (?,?,?,?,?,?,?)
    """, (
        sender, receiver, amount, flagged,
        str(datetime.now()), reference, status
    ))

    conn.commit()
    conn.close()

    # Go to OTP verification
    session["pending_tx"] = reference
    return redirect("/verify-otp")

    return redirect("/dashboard?transfer=success")

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
        pdf.cell(200,8,f"{r[1]} → {r[2]} | {r[3]} | FLAG:{r[4]} | REF:{r[6]}",ln=True)

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
