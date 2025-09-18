from flask import Flask, render_template, request, redirect, session, flash, url_for, send_from_directory
import sqlite3
import os

# in utils/app.py
app = Flask(__name__, template_folder='../frontend/pages', static_folder='../frontend')

from datetime import datetime, timedelta
from flask import jsonify

app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "users.db"))  # Fixed: removed ../utils/

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ✅ CORRECTED: Static file serving routes
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend/assets')
    return send_from_directory(assets_dir, filename)

@app.route('/frontend/<path:filename>')
def serve_frontend_static(filename):
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend')
    return send_from_directory(frontend_dir, filename)
@app.route('/frontend/static/<path:filename>')
def serve_frontend_static_files(filename):
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend/static')
    return send_from_directory(static_dir, filename)

@app.route("/test")
def test_page():
    return "✅ Test route is working"

@app.route('/')
def index():
    return render_template('login_page.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = cur.fetchone()
    conn.close()
    
    if user:
        session['user'] = username
        return redirect('/homepage')
    
    flash("Invalid username or password.")
    return redirect('/')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.form
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (first_name, last_name, username, password) VALUES (?, ?, ?, ?)',
                        (data['fname'], data['lname'], data['username'], data['password']))
            conn.commit()
            flash('User created successfully!')
        except sqlite3.IntegrityError:
            flash('Username already exists.')
        finally:
            conn.close()
        return render_template('signup_page.html')  # Stay on signup page with flash
    
    return render_template('signup_page.html')

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    show_password_fields = False
    password_updated = False
    verified_username = None  # To track verified user
    
    if "verified_username" in session:
        verified_username = session["verified_username"]
        show_password_fields = True
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "verify":
            fname = request.form.get("fname", "").strip()
            lname = request.form.get("lname", "").strip()
            username = request.form.get("username", "").strip()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                flash("❌ Username not found.")
            elif user[1].lower() != fname.lower():
                flash("❌ First name doesn't match.")
            elif user[2].lower() != lname.lower():
                flash("❌ Last name doesn't match.")
            else:
                # Verified successfully
                session["verified_username"] = username
                flash("✅ Verified. Now enter new password.")
                show_password_fields = True
                verified_username = username
        
        elif action == "reset":
            if "verified_username" not in session:
                flash("❌ Please verify your identity first.")
            else:
                new_password = request.form.get("new_password", "").strip()
                confirm_password = request.form.get("confirm_password", "").strip()
                
                if new_password != confirm_password:
                    flash("❌ Passwords do not match.")
                    show_password_fields = True
                elif not new_password:
                    flash("❌ Password cannot be empty.")
                    show_password_fields = True
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                                 (new_password, session["verified_username"]))
                    conn.commit()
                    cursor.execute("SELECT password FROM users WHERE username = ?", 
                                 (session["verified_username"],))
                    updated_pw = cursor.fetchone()
                    print("✅ DB password after update:", updated_pw)
                    conn.close()
                    
                    flash("✅ Password updated successfully!")
                    password_updated = True
                    session.pop("verified_username", None)
                    show_password_fields = False
    
    return render_template(
        "forgot_password.html",
        show_password_fields=show_password_fields,
        password_updated=password_updated,
        verified_username=verified_username
    )

@app.route("/homepage")
def homepage():
    if "user" not in session:
        flash("Please log in first.")
        return redirect("/")
    username = session["user"]
    return render_template("homepage.html", username=username)

@app.route("/mcp-agent")
def mcp_agent():
    username = session.get("user", "guest")  # fallback guest if no session user
    return render_template("MCPAgent.html", username=username)

@app.route('/chat-history/<username>')
def chat_history(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sender, message FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC", (username,))
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        messages.append({"sender": row["sender"], "message": row["message"]})
    
    return jsonify({"messages": messages})

@app.route("/reports")
def reports():
    return render_template("reports_page.html")

@app.route("/tdmdata")
def tdmdata():
    return render_template("TDMData.html")

@app.route('/patch_reports')
def patch_reports():
    if "user" not in session:
        flash("Please log in first.")
        return redirect('/')
    username = session["user"]
    return render_template('patch_reports.html', username=username)

@app.route("/test_data")
def test_data():
    return render_template("test_data.html")

@app.route("/testmanager")
def testmanager():
    return render_template("testmanager.html")

@app.route("/api-reports")
def apireports():
    return render_template("api-reports.html")


@app.route("/datarecon")
def datarecon():
    return render_template("datarecon.html")

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    flash("🔒 You have been logged out.")
    return redirect("/")

@app.route('/login_redirect')
def login_redirect():
    return redirect('/')

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        conn = sqlite3.connect('users.db')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print("users.db created.")
    
    app.run(debug=True)
