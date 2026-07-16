
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "unit4-demo-secret-key"
DB_PATH = Path(__file__).parent / "data" / "portal.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_user_id INTEGER NOT NULL,
            assigned_employee_id INTEGER,
            status TEXT NOT NULL,
            document_status TEXT NOT NULL,
            delay_reason TEXT,
            updated_by TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            customer_user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT COUNT(*) AS count FROM users")
    if cur.fetchone()["count"] == 0:
        users = [
            ("customer1", generate_password_hash("pass123"), "customer"),
            ("employee1", generate_password_hash("pass123"), "employee"),
            ("manager1", generate_password_hash("pass123"), "manager"),
        ]
        cur.executemany("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", users)
        conn.commit()
        cur.execute("SELECT id FROM users WHERE username='customer1'")
        customer_id = cur.fetchone()["id"]
        cur.execute("SELECT id FROM users WHERE username='employee1'")
        employee_id = cur.fetchone()["id"]
        orders = [
            ("ORD-1001", customer_id, employee_id, "Pending", "Missing", "Waiting on bill of lading", "system"),
            ("ORD-1002", customer_id, employee_id, "In Progress", "Received", "None", "system"),
            ("ORD-1003", customer_id, employee_id, "Delayed", "Missing", "Waiting on customer confirmation", "system"),
        ]
        cur.executemany("""
            INSERT INTO orders (order_number, customer_user_id, assigned_employee_id, status, document_status, delay_reason, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, orders)
        conn.commit()
    conn.close()


def login_required(role=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access denied for this role.")
                return redirect(url_for("home"))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


@app.route("/", methods=["GET"])
def home():
    if "role" not in session:
        return redirect(url_for("login"))
    if session["role"] == "customer":
        return redirect(url_for("customer_portal"))
    if session["role"] == "employee":
        return redirect(url_for("employee_portal"))
    if session["role"] == "manager":
        return redirect(url_for("manager_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/customer", methods=["GET", "POST"])
@login_required("customer")
def customer_portal():
    conn = get_db()
    if request.method == "POST":
        order_id = request.form.get("order_id")
        message = request.form.get("message", "").strip()
        if message:
            conn.execute("INSERT INTO requests (order_id, customer_user_id, message) VALUES (?, ?, ?)",
                         (order_id, session["user_id"], message))
            conn.commit()
            flash("Request submitted for manager review.")
        else:
            flash("Request message is required.")
    orders = conn.execute("SELECT * FROM orders WHERE customer_user_id=?", (session["user_id"],)).fetchall()
    requests_list = conn.execute("SELECT r.*, o.order_number FROM requests r JOIN orders o ON r.order_id=o.id WHERE r.customer_user_id=? ORDER BY r.created_at DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("customer.html", orders=orders, requests_list=requests_list)


@app.route("/employee", methods=["GET", "POST"])
@login_required("employee")
def employee_portal():
    conn = get_db()
    if request.method == "POST":
        order_id = request.form.get("order_id")
        status = request.form.get("status")
        document_status = request.form.get("document_status")
        delay_reason = request.form.get("delay_reason", "").strip() or "None"
        conn.execute("""
            UPDATE orders
            SET status=?, document_status=?, delay_reason=?, updated_by=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (status, document_status, delay_reason, session["username"], order_id))
        conn.commit()
        flash("Workflow record updated.")
    orders = conn.execute("SELECT * FROM orders ORDER BY updated_at DESC").fetchall()
    conn.close()
    return render_template("employee.html", orders=orders)


@app.route("/manager")
@login_required("manager")
def manager_dashboard():
    conn = get_db()
    stats = {
        "total": conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"],
        "missing_docs": conn.execute("SELECT COUNT(*) AS count FROM orders WHERE document_status='Missing'").fetchone()["count"],
        "delayed": conn.execute("SELECT COUNT(*) AS count FROM orders WHERE status='Delayed'").fetchone()["count"],
        "open_requests": conn.execute("SELECT COUNT(*) AS count FROM requests WHERE status='Open'").fetchone()["count"],
    }
    orders = conn.execute("SELECT * FROM orders ORDER BY updated_at DESC").fetchall()
    requests_list = conn.execute("SELECT r.*, o.order_number FROM requests r JOIN orders o ON r.order_id=o.id ORDER BY r.created_at DESC").fetchall()
    conn.close()
    return render_template("manager.html", stats=stats, orders=orders, requests_list=requests_list)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
