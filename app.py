from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import random
import string
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "super-secret-key"

DB = "bank.db"

# ---------------- MAIL CONFIG ----------------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "your_email@gmail.com"
app.config["MAIL_PASSWORD"] = "your_app_password"

mail = Mail(app)

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # USERS
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        account_number TEXT UNIQUE
    )
    """)

    # TRANSACTIONS
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_account TEXT,
        receiver_account TEXT,
        amount REAL,
        created_at TEXT,
        reference TEXT,
        status TEXT DEFAULT 'PENDING'
    )
    """)

    # OTPs
    c.execute("""
    CREATE TABLE IF NOT EXISTS otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT,
        otp TEXT,
        created_at TEXT
    )
    """)

    @app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT is_admin FROM users WHERE username=?", (session["user"],))
    if not c.fetchone()[0]:
        conn.close()
        return "Unauthorized"

    c.execute("""
        SELECT sender_account, receiver_account, amount, reference, status, created_at
        FROM transactions ORDER BY id DESC
    """)
    txns = c.fetchall()

    conn.close()
    return render_template("admin.html", txns=txns)
init_db()

# ---------------- HELPERS ----------------
def generate_account():
    return str(random.randint(1000000000, 9999999999))

def generate_reference():
    return "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_otp():
    return str(random.randint(100000, 999999))

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

# ---------- AUTH ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        account = generate_account()

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute(
            "INSERT INTO users (username, password, email, account_number) VALUES (?,?,?,?)",
            (username, generate_password_hash(password), email, account)
        )

        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user"] = user[1]
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT username, balance, account_number FROM users WHERE username=?", (session["user"],))
    user = c.fetchone()

    c.execute(
        "SELECT sender_account, receiver_account, amount, reference, status, created_at FROM transactions "
        "WHERE sender_account=? OR receiver_account=? ORDER BY id DESC",
        (user[2], user[2])
    )
    txns = c.fetchall()

    conn.close()
    return render_template("dashboard.html", user=user, txns=txns)
    
    from fpdf import FPDF
from flask import send_file

@app.route("/statement")
def statement():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT account_number FROM users WHERE username=?", (session["user"],))
    acc = c.fetchone()[0]

    c.execute("""
        SELECT sender_account, receiver_account, amount, reference, status, created_at
        FROM transactions
        WHERE sender_account=? OR receiver_account=?
    """, (acc, acc))
    rows = c.fetchall()

    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Scotitrust-Bank Statement", ln=True)
    pdf.ln(5)

    for r in rows:
        pdf.multi_cell(0, 8,
            f"{r[5][:19]} | {r[0]} → {r[1]} | ₦{r[2]} | {r[3]} | {r[4]}"
        )

    filename = f"{acc}_statement.pdf"
    pdf.output(filename)

    return send_file(filename, as_attachment=True)


# ---------- TRANSFER ----------
@app.route("/transfer", methods=["POST"])
def transfer():
    if "user" not in session:
        return redirect("/login")

    receiver_account = request.form["receiver_account"]
    amount = float(request.form["amount"])

status = "FLAGGED" if amount >= 500000 else "PENDING"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # sender
    c.execute("SELECT account_number, balance, email FROM users WHERE username=?", (session["user"],))
    sender = c.fetchone()

    # receiver
    c.execute("SELECT account_number FROM users WHERE account_number=?", (receiver_account,))
    receiver = c.fetchone()

    if not receiver or sender[1] < amount:
        conn.close()
        return "Transfer failed", 400

    reference = generate_reference()

    # create transaction (PENDING)
    c.execute("""
        INSERT INTO transactions 
        (sender_account, receiver_account, amount, created_at, reference, status)
        VALUES (?,?,?,?,?,?)
    """, (
        sender[0],
        receiver_account,
        amount,
        datetime.now().isoformat(),
        reference,
        "PENDING"
    ))

    # generate OTP
    otp = generate_otp()
    c.execute(
        "INSERT INTO otps (reference, otp, created_at) VALUES (?,?,?)",
        (reference, otp, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

    # send OTP email
    msg = Message(
        subject="Your Transfer OTP",
        sender=app.config["MAIL_USERNAME"],
        recipients=[sender[2]],
        body=f"Your OTP for transfer {reference} is {otp}"
    )
    mail.send(msg)

    return render_template("verify_otp.html", reference=reference)

# ---------- VERIFY OTP ----------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    reference = request.form["reference"]
    otp_input = request.form["otp"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT otp FROM otps WHERE reference=? ORDER BY id DESC LIMIT 1", (reference,))
    row = c.fetchone()

    if row and row[0] == otp_input:
        # get transaction
        c.execute("SELECT sender_account, receiver_account, amount FROM transactions WHERE reference=?", (reference,))
        txn = c.fetchone()

        # update balances
        c.execute("UPDATE users SET balance = balance - ? WHERE account_number=?", (txn[2], txn[0]))
        c.execute("UPDATE users SET balance = balance + ? WHERE account_number=?", (txn[2], txn[1]))

        # mark success
        c.execute("UPDATE transactions SET status='SUCCESS' WHERE reference=?", (reference,))
        conn.commit()

        # email confirmation
        c.execute("SELECT email FROM users WHERE account_number=?", (txn[0],))
        email = c.fetchone()[0]

        msg = Message(
            subject="Transaction Successful",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email],
            body=f"Your transfer {reference} was successful."
        )
        mail.send(msg)

        conn.close()
        return redirect("/dashboard")

    conn.close()
    return "Invalid OTP", 400


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
