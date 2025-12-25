import os
import sqlite3
import random
from datetime import datetime

from flask import Flask, render_template, request, redirect, session, send_file
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF

# ✅ CREATE APP FIRST
app = Flask(__name__)

# ✅ THEN configure it
app.secret_key = "super-secret-key"

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")

mail = Mail(app)

@app.route("/")
def home():
    return render_template("index.html")
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        confirm_password = request.form["confirm_password"]
        phone = request.form.get("phone", "")

        # Password confirmation check
        if password != generate_password_hash(confirm_password):
            return "Passwords do not match"

        # Generate a 10-digit account number
        account_number = str(random.randint(1000000000, 9999999999))
        reference = f"REG-{random.randint(100000,999999)}"

        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            # Insert user data
            c.execute(
                "INSERT INTO users (username, password, balance, account_number, email) VALUES (?,?,?,?,?)",
                (fullname, password, 0, account_number, email)
            )
            conn.commit()

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
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
                body=f"Hello {fullname}, your OTP for Scotitrust-Bank registration is: {otp_code}"
            )
            mail.send(msg)

            return redirect(f"/verify_otp?ref={reference}&user={fullname}")

        except sqlite3.IntegrityError:
            return "Email already exists or account number collision. Please try again."

    return render_template("register.html")

@app.route("/login")
def login():
    return "Login page"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
