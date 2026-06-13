from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import random
import string

app = Flask(__name__)
app.secret_key = "band_secret_key"


# ======================
# DB
# ======================

def get_db():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        group_code TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        name TEXT,
        part TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reflections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        date TEXT,
        name TEXT,
        part TEXT,
        reflection TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_reflections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        date TEXT,
        reflection TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS part_reflections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        date TEXT,
        part TEXT,
        reflection TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ======================
# ログインチェック
# ======================


from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "group_id" not in session:
            return redirect("/")

        return f(*args, **kwargs)

    return decorated_function


# ======================
# 団体コード生成
# ======================

def generate_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8
        )
    )


# ======================
# ログイン
# ======================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        code = request.form["group_code"]

        conn = get_db()
        group = conn.execute(
            "SELECT * FROM groups WHERE group_code=?",
            (code,)
        ).fetchone()

        conn.close()

        if group:
            session["group_id"] = group["id"]
            return redirect("/home")

    return render_template("login.html")


# ======================
# 団体作成
# ======================

@app.route("/create_group", methods=["GET", "POST"])
def create_group():

    if request.method == "POST":

        name = request.form["group_name"]
        code = generate_code()

        conn = get_db()

        conn.execute(
            """
            INSERT INTO groups
            (group_name,group_code)
            VALUES (?,?)
            """,
            (name, code)
        )

        conn.commit()
        conn.close()

        return render_template(
            "create_group.html",
            code=code
        )

    return render_template(
        "create_group.html",
        code=None
    )


# ======================
# ホーム
# ======================

@app.route("/home")
@login_required
def home():

    if "group_id" not in session:
        return redirect("/")

    conn = get_db()

    group = conn.execute(
        "SELECT * FROM groups WHERE id=?",
        (session["group_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "home.html",
        group=group
    )


# ======================
# ログアウト
# ======================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ======================
# 団体名変更
# ======================

@app.route("/edit_group", methods=["GET", "POST"])
def edit_group():

    if "group_id" not in session:
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        name = request.form["group_name"]

        conn.execute(
            """
            UPDATE groups
            SET group_name=?
            WHERE id=?
            """,
            (name, session["group_id"])
        )

        conn.commit()

    group = conn.execute(
        "SELECT * FROM groups WHERE id=?",
        (session["group_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "edit_group.html",
        group=group
    )


# ======================
# メンバー管理
# ======================

@app.route("/members", methods=["GET", "POST"])
@login_required
def members():

    if "group_id" not in session:
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        name = request.form["name"]
        part = request.form["part"]

        conn.execute(
            """
            INSERT INTO members
            (group_id,name,part)
            VALUES (?,?,?)
            """,
            (session["group_id"], name, part)
        )

        conn.commit()

    members = conn.execute(
        """
        SELECT * FROM members
        WHERE group_id=?
        """,
        (session["group_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "members.html",
        members=members
    )


@app.route("/delete_member/<int:id>")
def delete_member(id):

    conn = get_db()

    conn.execute(
    """
    DELETE FROM members
    WHERE id=?
    AND group_id=?
    """,
    (id, session["group_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/members")


# ======================
# 個人反省
# ======================

@app.route("/add_reflection", methods=["GET", "POST"])
@login_required
def add_reflection():

    if "group_id" not in session:
        return redirect("/")

    conn = get_db()

    members = conn.execute(
        """
        SELECT * FROM members
        WHERE group_id=?
        """,
        (session["group_id"],)
    ).fetchall()

    if request.method == "POST":

        conn.execute(
            """
            INSERT INTO reflections
            (group_id,date,name,part,reflection)
            VALUES (?,?,?,?,?)
            """,
            (
                session["group_id"],
                request.form["date"],
                request.form["name"],
                request.form["part"],
                request.form["reflection"]
            )
        )

        conn.commit()
        conn.close()

        return redirect("/reflections")

    conn.close()

    return render_template(
        "add_reflection.html",
        members=members
    )


# ======================
# 全体反省
# ======================

@app.route("/add_group_reflection", methods=["GET", "POST"])
def add_group_reflection():

    if request.method == "POST":

        conn = get_db()

        conn.execute(
            """
            INSERT INTO group_reflections
            (group_id,date,reflection)
            VALUES (?,?,?)
            """,
            (
                session["group_id"],
                request.form["date"],
                request.form["reflection"]
            )
        )

        conn.commit()
        conn.close()

        return redirect("/home")

    return render_template(
        "add_group_reflection.html"
    )


# ======================
# パート反省
# ======================

@app.route("/add_part_reflection", methods=["GET", "POST"])
def add_part_reflection():

    if request.method == "POST":

        conn = get_db()

        conn.execute(
            """
            INSERT INTO part_reflections
            (group_id,date,part,reflection)
            VALUES (?,?,?,?)
            """,
            (
                session["group_id"],
                request.form["date"],
                request.form["part"],
                request.form["reflection"]
            )
        )

        conn.commit()
        conn.close()

        return redirect("/home")

    return render_template(
        "add_part_reflection.html"
    )


# ======================
# 一覧
# ======================

@app.route("/reflections")
def reflections():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT * FROM reflections
        WHERE group_id=?
        ORDER BY date DESC
        """,
        (session["group_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "reflections.html",
        rows=rows
    )


# ======================
# 反省編集
# ======================

@app.route(
    "/edit_reflection/<int:id>",
    methods=["GET", "POST"]
)
def edit_reflection(id):

    conn = get_db()

    if request.method == "POST":

        reflection = request.form["reflection"]

        conn.execute(
            """
            UPDATE reflections
            SET reflection=?
            WHERE id=?
            AND group_id=?
            """,
            (
                reflection,
                id,
                session["group_id"]
            )
        )

        conn.commit()

        return redirect("/reflections")

    conn.execute(
    """
    DELETE FROM members
    WHERE id=?
    AND group_id=?
    """,
    (id, session["group_id"])
)

    conn.close()

    return render_template(
        "edit_reflection.html",
        row=row
    )


# ======================
# 反省削除
# ======================

@app.route("/delete_reflection/<int:id>")
def delete_reflection(id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM reflections
        WHERE id=?
        AND group_id=?
        """,
        (id, session["group_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/reflections")


# ======================
# 検索
# ======================

@app.route("/search", methods=["GET", "POST"])
def search():

    results = []

    if request.method == "POST":

        keyword = request.form["keyword"]

        conn = get_db()

        results = conn.execute(
            """
            SELECT * FROM reflections
            WHERE group_id=?
            AND (
                name LIKE ?
                OR part LIKE ?
                OR reflection LIKE ?
                OR date LIKE ?
            )
            """,
            (
                session["group_id"],
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%"
            )
        ).fetchall()

        conn.close()

    return render_template(
        "search.html",
        results=results
    )


import os

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )