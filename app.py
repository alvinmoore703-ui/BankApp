import os
from flask import Flask, render_template, request, redirect
import sqlite3, random, os
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ---------------- MAIL CONFIG ----------------
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD")
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
        full_name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        account_number TEXT UNIQUE,
        email TEXT,
        verified INTEGER DEFAULT 0
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
    conn.commit()
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return "Passwords do not match!"

        hashed_password = generate_password_hash(password)
        account_number = str(random.randint(1000000000, 9999999999))  # 10-digit

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            # Save user
            c.execute("""
                INSERT INTO users (full_name, username, password, balance, account_number, email)
                VALUES (?,?,?,?,?,?)
            """, (full_name, username, hashed_password, 1000, account_number, email))
            conn.commit()

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            reference = f"REG-{random.randint(100000,999999)}"
            c.execute("""
                INSERT INTO otps (reference, otp, created_at) VALUES (?,?,?)
            """, (reference, otp_code, str(datetime.now())))
            conn.commit()
            conn.close()

            # Send OTP email
            msg = Message(
                subject="Verify Your Scotitrust-Bank Account",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email],
                body=f"Hi {full_name}, your OTP to verify your Scotitrust-Bank account is: {otp_code}"
            )
            mail.send(msg)

            return redirect(f"/verify_otp?ref={reference}&user={username}")

        except sqlite3.IntegrityError:
            return "Username or email already exists, or account number collision!"

    return render_template("register.html")
