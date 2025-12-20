from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from datetime import datetime, timedelta
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "bank.db"
DAILY_LIMIT = 2000

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 1000,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender INTEGER,
        receiver INTEGER,
        amount REAL,
        date TEXT,
        status TEXT DEFAULT 'pending',
        risk_score INTEGER DEFAULT 0
    );
    """)
    db.commit()

init_db()

# ---------------- FRAUD LOGIC ----------------
def fraud_score(user_created, amount, total_today):
    score = 0
    if total_today + amount > DAILY_LIMIT:
        score += 40
    if amount > 1000:
        score += 25
    if datetime.now() - user_created < timedelta(days=1):
        score += 15
    return score

# ---------------- AUTH ----------------
@app.route("/", methods=["GET", "HEAD"])
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO users(username,password,created_at) VALUES(?,?,?)",
            (
                request.form["username"],
                generate_password_hash(request.form["password"]),
                datetime.now().isoformat()
            )
        )
        db.commit()
        return redirect("/")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?",
        (session["user_id"],)).fetchone()

    users = db.execute("SELECT id,username FROM users WHERE id!=?",
        (user["id"],)).fetchall()

    tx = db.execute("""
        SELECT * FROM transactions
        WHERE sender=? OR receiver=?
        ORDER BY id DESC
    """,(user["id"],user["id"])).fetchall()

    return render_template("dashboard.html",
        user=user,
        users=users,
        transactions=tx,
        daily_limit=DAILY_LIMIT)

# ---------------- SEND MONEY ----------------
@app.route("/send", methods=["POST"])
def send():
    db = get_db()
    sender = db.execute("SELECT * FROM users WHERE id=?",
        (session["user_id"],)).fetchone()

    amount = float(request.form["amount"])
    receiver = int(request.form["to_user"])

    today = datetime.now().date().isoformat()
    total_today = db.execute("""
        SELECT COALESCE(SUM(amount),0) FROM transactions
        WHERE sender=? AND date LIKE ?
    """,(sender["id"], f"{today}%")).fetchone()[0]

    risk = fraud_score(
        datetime.fromisoformat(sender["created_at"]),
        amount,
        total_today
    )

    status = "pending" if risk >= 60 else "approved"

    if status == "approved" and sender["balance"] >= amount:
        db.execute("UPDATE users SET balance=balance-? WHERE id=?",
            (amount,sender["id"]))
        db.execute("UPDATE users SET balance=balance+? WHERE id=?",
            (amount,receiver))

    db.execute("""
        INSERT INTO transactions(sender,receiver,amount,date,status,risk_score)
        VALUES(?,?,?,?,?,?)
    """,(sender["id"],receiver,amount,
         datetime.now().isoformat(),status,risk))

    db.commit()
    return redirect("/dashboard")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/")

    db = get_db()
    flagged = db.execute("""
        SELECT t.*, u.username FROM transactions t
        JOIN users u ON t.sender=u.id
        WHERE t.status='pending'
    """).fetchall()

    return render_template("admin.html", flagged=flagged)

@app.route("/approve/<int:tid>", methods=["POST"])
def approve(tid):
    db = get_db()
    tx = db.execute("SELECT * FROM transactions WHERE id=?",(tid,)).fetchone()

    db.execute("UPDATE users SET balance=balance-? WHERE id=?",
        (tx["amount"],tx["sender"]))
    db.execute("UPDATE users SET balance=balance+? WHERE id=?",
        (tx["amount"],tx["receiver"]))
    db.execute("UPDATE transactions SET status='approved' WHERE id=?",(tid,))
    db.commit()
    return redirect("/admin")

@app.route("/reject/<int:tid>", methods=["POST"])
def reject(tid):
    db = get_db()
    db.execute("UPDATE transactions SET status='rejected' WHERE id=?",(tid,))
    db.commit()
    return redirect("/admin")

# ---------------- PDF STATEMENT ----------------
@app.route("/statement")
def statement():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?",
        (session["user_id"],)).fetchone()

    tx = db.execute("""
        SELECT * FROM transactions
        WHERE sender=? OR receiver=?
    """,(user["id"],user["id"])).fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,"SCOTITRUST BANK STATEMENT",ln=True)
    pdf.set_font("Arial","",10)
    pdf.cell(0,10,f"Account: {user['username']}",ln=True)

    for t in tx:
        pdf.cell(0,8,
            f"{t['date']} | £{t['amount']} | {t['status']} | Risk {t['risk_score']}",
            ln=True)

    file = "statement.pdf"
    pdf.output(file)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
