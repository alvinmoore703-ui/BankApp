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
        return redirect("/")

    return render_template("register.html")

@app.route("/login")
def login():
    return "Login page"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
