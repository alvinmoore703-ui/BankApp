import os
import sqlite3
import random

from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF
from flask_mail import Mail, Message

@app.route("/")
def home():
    return "Scotitrust Bank OK"
    
@app.route("/login")
def login():
    return "Login page"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
