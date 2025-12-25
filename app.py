import os
import sqlite3
import random

from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF
from flask_mail import Mail, Message

app.secret_key = "super-secret-key"

# Mail config (uses Render Environment Variables)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return "Login page"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
