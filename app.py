from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
import os, random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

# ================= MAIL CONFIG =================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

mail = Mail(app)

# ================= TEMP DATABASE (IN-MEMORY) =================
users = {}

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        account_type = request.form["account_type"]

        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        if email in users:
            flash("Email already registered")
            return redirect(url_for("register"))

        account_number = "30" + str(random.randint(10000000, 99999999))
        otp = str(random.randint(100000, 999999))

        users[email] = {
            "fullname": fullname,
            "password": password,
            "account": account_number,
            "balance": 10000,
            "otp": otp,
            "verified": True,
            "type": account_type
        }

        msg = Message("Scotitrust Bank OTP", recipients=[email])
        msg.body = f"Your verification code is: {otp}"
        mail.send(msg)

        session["verify_email"] = email
        return redirect(url_for("verify"))

    return render_template("register.html")

# ================= OTP VERIFY =================
@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("verify_email")

    if not email:
        return redirect(url_for("register"))

    if request.method == "POST":
        otp = request.form["otp"]

        if users[email]["otp"] == otp:
            users[email]["verified"] = True
            flash("Account verified. Please log in.")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP")

    return render_template("verify.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = users.get(email)

        if not user or user["password"] != password:
            flash("Invalid email or password")
            return redirect(url_for("login"))

        if not user["verified"]:
            flash("Please verify your account first")
            return redirect(url_for("login"))

        session["user"] = email

        # redirect by account type
        if user["type"] == "personal":
            return redirect(url_for("personal"))
        elif user["type"] == "business":
            return redirect(url_for("business"))
        else:
            return redirect(url_for("private"))

    return render_template("login.html")

# ================= DASHBOARDS =================
@app.route("/personal")
def personal():
    return render_dashboard("personal")

@app.route("/business")
def business():
    return render_dashboard("business")

@app.route("/private")
def private():
    return render_dashboard("private")

def render_dashboard(required_type):
    if "user" not in session:
        return redirect(url_for("login"))

    user = users[session["user"]]

    if user["type"] != required_type:
        flash("Access denied")
        return redirect(url_for("home"))

    return render_template("dashboard.html", user=user)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
