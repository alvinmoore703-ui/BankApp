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

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        account_number TEXT UNIQUE,
        email TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS otps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT,
        otp TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        email = request.form["email"]
        account_number = str(random.randint(1000000000, 9999999999))

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
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

            return redirect(f"/verify_otp?ref={reference}&user={username}")

        except sqlite3.IntegrityError:
            return "Username already exists or account number collision"

    return render_template("register.html")

# ---------------- VERIFY OTP ----------------
@app.route("/verify_otp", methods=["GET","POST"])
def verify_otp():
    reference = request.args.get("ref")
    username = request.args.get("user")

    if request.method == "POST":
        entered_otp = request.form["otp"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT otp FROM otps WHERE reference=?", (reference,))
        result = c.fetchone()

        if result and result[0] == entered_otp:
            # Mark user as verified
            c.execute("UPDATE users SET verified=1 WHERE username=?", (username,))
            c.execute("DELETE FROM otps WHERE reference=?", (reference,))
            conn.commit()
            conn.close()
            return redirect("/login")
        conn.close()
        return "Invalid OTP. Please try again."

    return render_template("verify_otp.html", reference=reference, username=username)
    
# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            if not user[7]:  # verified column index
                return "Your account is not verified. Please check your email for the OTP."

            if check_password_hash(user[2], password):
                session["user"] = username
                session["admin"] = user[4]
                return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")
