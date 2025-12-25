from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, os, random
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ---------------- MAIL CONFIG ----------------
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME="your_email@gmail.com",
    MAIL_PASSWORD="your_password"
)
mail = Mail(app)

DB = "bank.db"

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        account_number TEXT UNIQUE,
        email TEXT
    )
    """)

    # Transactions table
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount REAL,
        flagged INTEGER DEFAULT 0,
        created_at TEXT,
        reference TEXT,
        status TEXT
    )
    """)

    # KYC table
    c.execute("""
    CREATE TABLE IF NOT EXISTS kyc (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        full_name TEXT,
        dob TEXT,
        address TEXT,
        verified INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    # OTP table
    c.execute("""
    CREATE TABLE IF NOT EXISTS otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT,
        otp TEXT,
        created_at TEXT
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
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        import random
        from flask_mail import Message

        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        email = request.form["email"]
        account_number = str(random.randint(1000000000, 9999999999))  # 10-digit account

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            # Insert user with balance 1000
            c.execute(
                "INSERT INTO users (username,password,balance,account_number,email) VALUES (?,?,?,?,?)",
                (username, password, 1000, account_number, email)
            )
            conn.commit()

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            reference = f"REG-{random.randint(100000,999999)}"
            c.execute(
                "INSERT INTO otps (reference, otp, created_at) VALUES (?,?,?)",
                (reference, otp_code, str(datetime.now()))
            )
            conn.commit()
            conn.close()

            # Send OTP email
            msg = Message(
                subject="Verify Your Scotitrust-Bank Account",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email],
                body=f"Welcome {username}! Your OTP to verify your account is: {otp_code}"
            )
            mail.send(msg)

            # Redirect to OTP verification page
            return redirect(f"/verify_otp?ref={reference}&user={username}")

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

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT balance, account_number FROM users WHERE username=?", (session["user"],))
    balance, account_number = c.fetchone()

    c.execute("SELECT * FROM transactions WHERE sender=? OR receiver=?",
              (session["user"], session["user"]))
    tx = c.fetchall()
    conn.close()

    return render_template("dashboard.html", balance=balance, account_number=account_number, tx=tx)

@app.route("/transfer", methods=["POST"])
def transfer():
    sender = session["user"]
    receiver = request.form["to"]
    amount = float(request.form["amount"])
    tx_ref = f"TX{random.randint(100000,999999)}"
    flagged = 1 if amount > 5000 else 0
    status = "FLAGGED" if amount >= 500000 else "SUCCESS"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Get sender balance
    c.execute("SELECT balance, email FROM users WHERE username=?", (sender,))
    bal, user_email = c.fetchone()
    if bal < amount:
        conn.close()
        return "Insufficient funds"

    # Update balances
    c.execute("UPDATE users SET balance=balance-? WHERE username=?", (amount,sender))
    c.execute("UPDATE users SET balance=balance+? WHERE username=?", (amount,receiver))

    # Insert transaction
    c.execute("""INSERT INTO transactions 
        (sender, receiver, amount, flagged, created_at, reference, status)
        VALUES (?,?,?,?,?,?,?)""",
        (sender,receiver,amount,flagged,str(datetime.now()),tx_ref,status)
    )

    conn.commit()
    conn.close()

    # Send email alert
    msg = Message(
        subject="Transaction Successful",
        sender=app.config["MAIL_USERNAME"],
        recipients=[user_email],
        body=f"Your transfer {tx_ref} was successful."
    )
    mail.send(msg)

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
        pdf.cell(200,8,f"{r[1]} → {r[2]} | {r[3]} | Status:{r[7]} | REF:{r[6]}",ln=True)

    path = f"{user}_statement.pdf"
    pdf.output(path)
    return send_file(path, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- REST API ----------------
@app.route("/api/balance/<username>", methods=["GET"])
def api_balance(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"username": username, "balance": result[0]}
    return {"error": "User not found"}, 404

@app.route("/api/transactions/<username>", methods=["GET"])
def api_transactions(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sender, receiver, amount, flagged, reference, created_at, status FROM transactions WHERE sender=? OR receiver=?", (username, username))
    rows = c.fetchall()
    conn.close()
    return {"transactions": rows}

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
