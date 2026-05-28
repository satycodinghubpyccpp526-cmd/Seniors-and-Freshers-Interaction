from flask import Flask, render_template, request, redirect, jsonify, session
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key="college_secret"

DATABASE_URL = os.getenv("DATABASE_URL")
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute(''' CREATE TABLE IF NOT EXISTS tips(id SERIAL PRIMARY KEY,
              senior_name TEXT,
              college TEXT,
              branch TEXT,
              title TEXT,
              description TEXT,
              urgency TEXT,
              credibility INTEGER DEFAULT 0,
              verified INTEGER DEFAULT 0,
              likes INTEGER DEFAULT 0,
              created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,
              username TEXT UNIQUE,
              password TEXT,
              role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments(id SERIAL PRIMARY KEY,
              tip_id INTEGER,
              username TEXT,
              comment TEXT,
              created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications(id SERIAL PRIMARY KEY,
              username TEXT,
              message TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks(id SERIAL PRIMARY KEY,
              username TEXT,
              tip_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS liked_tips(id SERIAL PRIMARY KEY,
              csername TEXT,
              tip_id INTEGER)''')
    conn.commit()
    conn.close()
    
init_db()

@app.route("/")
def home():
    
    college = request.args.get("college")
    branch = request.args.get("branch")
    urgency = request.args.get("urgency")
    keyword = request.args.get("keyword")
    
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM tips WHERE 1=1"
    params = []
    
    if college:
        query += " AND college=%s"
        params.append(college)
        
    if branch:
        query += " AND branch=%s"
        params.append(branch)
        
    if urgency:
        query += " AND urgency=%s"
        params.append(urgency)
        
    if keyword:
        query += " AND title LIKE %s"
        params.append("%"+keyword+"%")

    query += " ORDER BY likes DESC"
    c.execute(query, params)
    tips = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM tips")
    total_tips = c.fetchone()[0]
    
    c.execute("SELECT * FROM comments")
    comments = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM tips WHERE verified=1")
    verified_tips = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
  
    conn.close()

    return render_template("index.html", tips=tips, total_tips=total_tips,verified_tips = verified_tips, total_users=total_users, comments=comments)

@app.route("/add_tip", methods=["POST"])
def add_tip():
    
    if "user" not in session:
        return redirect("/login")

    senior_name = request.form["senior_name"]
    college = request.form["college"]
    branch = request.form["branch"]
    title = request.form["title"]
    description = request.form["description"]
    urgency = request.form["urgency"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""INSERT INTO tips(senior_name, college, branch, title, description, urgency, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        senior_name,
        college,
        branch,
        title,
        description,
        urgency,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/signup",methods = ["GET","POST"])
def signup():
    if request.method=="POST":
        
        username=request.form["username"]
        password=request.form["password"]
        role=request.form["role"]

        conn=get_db()
        c=conn.cursor()
        c.execute("INSERT INTO users(username,password,role) VALUES(%s,%s,%s)",(username,password,role))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("signup.html")

@app.route("/login",methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        
        c.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",(username, password)
        )
        user = c.fetchone()
        conn.close()
        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/")
        else:
            return "Invalid Username or Password"
        
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/contributions")
def my_contributions(id):
    if "user" not in session:
        return redirect("/login")
    username = session["user"]
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tips WHERE senior_name=%s", (username, ))
    
    total_tips = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM comments WHERE username=%s", (username, ))
    
    total_comments = c.fetchone()[0]
    
    conn.close()
    
    return render_template(
        "contibution.html",
        total_tips=total_tips,
        total_comments=total_comments
    )

@app.route("/my_tips")
def my_tips():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM tips WHERE senior_name=%s",
        (session["user"],)
    )

    tips = c.fetchall()

    conn.close()

    return render_template(
        "mytips.html",
        tips=tips
    )

@app.route("/notifications")
def notifications():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM notifications WHERE username=%s",
        (session["user"],)
    )

    data = c.fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=data
    )

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    return render_template(
        "profile.html",
        username=session["user"],
        role=session["role"]
    )

@app.route("/verify/<int:id>")
def verify(id):
    if session.get("role") != "Admin":
        return "Access Denied"
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tips SET verified=1, credibility=credibility+1 WHERE id=%s",(id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    if session.get("role") != "Admin":
        return "Access Denied"
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tips WHERE id=%s",(id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/like/<int:id>")
def like(id):

    conn=get_db()
    c=conn.cursor()

    c.execute(
        "UPDATE tips SET likes=likes+1 WHERE id=%s",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/edit/<int:id>")
def edit(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method=="POST":
        
        title = request.form["title"]
        description = request.form["description"]
        
        c.execute(
            "UPDATE tips SET title=%s, WHERE id=%s",(title,description,id)
        )
        
        conn.commit()
        conn.close()
        
        return redirect("/")
    
    c.execute(
        "SELECT * FROM tips WHERE id=%s",(id, )
    )
    
    tip=c.fetchone()
    
    conn.close()
    
    return render_template(
        "edit.html",
        tip=tip
    )

@app.route("/bookmark/<int:id>")
def bookmark(id):

    if "user" not in session:
        return redirect("/login")

    conn=get_db()
    c=conn.cursor()

    c.execute(
        "INSERT INTO bookmarks(username,tip_id) VALUES(%s,%s)",
        (
            session["user"],
            id
        )
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/comment/<int:id>", methods=["POST"])
def comment(id):

    if "user" not in session:
        return redirect("/login")

    comment = request.form["comment"]

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO comments(tip_id,username,comment) VALUES(%s,%s,%s)",
        (
            id,
            session["user"],
            comment
        )
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/saved")
def saved():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT tips.* FROM tips
              JOIN bookmarks
              ON tips.id = bookmarks.tip_id
              WHERE bookmarks.username=%s''',(session["user"],))
    
    tips = c.fetchall()
    
    conn.close()
    
    return render_template(
        "saved.html",
        tips=tips
    )
    
@app.route("/recent")
def recent():
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute(
        "SELECT * FROM tips ORDER BY created_at DESC LIMIT 5"
    )
    
    tips = c.fetchall()
    
    conn.close()
    
    return render_template(
        "recent.html",
        tips=tips
    )

@app.route("/recommend/<branch>")
def recommend(branch):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM tips WHERE branch=%s",
        (branch,)
    )

    tips = c.fetchall()

    conn.close()

    return render_template(
        "recommend.html",
        tips=tips,
        branch=branch
    )
    
@app.route("/dashboard")
def dashboard():
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute(
        "SELECT COUNT(*) FROM tips"
    )
    total_tips=c.fetchone()[0]
    
    c.execute(
        "SELECT COUNT(*) FROM users"
    )
    total_users=c.fetchone()[0]
    
    c.execute(
        "SELECT SUM(likes) FROM tips"
    )
    total_likes=c.fetchone()[0]
    
    conn.close()
    
    return render_template(
        "dashboard.html",
        total_tips=total_tips,
        total_users=total_users,
        total_likes=total_likes,
    )

@app.route("/tips", methods = ["GET"])
def get_tips():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM tips")
    rows = c.fetchall()
    conn.close()
    tips = []
    
    for row in rows:
        tips.append({
            "id": row[0],
            "senior_name": row[1],
            "college": row[2],
            "branch": row[3],
            "title": row[4],
            "description": row[5],
            "urgency": row[6],
            "credibility": row[7],
            "created_at": row[8]
        })
    return jsonify(tips)

@app.route("/add_likes_column")
def add_likes_column():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("ALTER TABLE tips ADD COLUMN likes INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()
    
    return "Likes column added"

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "404.html"
    ),404

if __name__ == "__main__":
    app.run(debug = True)
