from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
import random
import string
import os
from datetime import timedelta

# ======================
# アプリ初期化
# ======================
app = Flask(__name__)

app.config["SECRET_KEY"] = "band_app_super_secret_2026_stable"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# セッション安定化
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"


# ======================
# モデル
# ======================
class Group(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100))
    group_code = db.Column(db.String(20), unique=True)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    name = db.Column(db.String(100))
    part = db.Column(db.String(100))


class Reflection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    date = db.Column(db.String(20))
    name = db.Column(db.String(100))
    part = db.Column(db.String(100))
    reflection = db.Column(db.Text)


class GroupReflection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    date = db.Column(db.String(20))
    reflection = db.Column(db.Text)


class PartReflection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    date = db.Column(db.String(20))
    part = db.Column(db.String(100))
    reflection = db.Column(db.Text)


# ======================
# DB作成
# ======================
with app.app_context():
    db.create_all()


# ======================
# ユーザーロード
# ======================
@login_manager.user_loader
def load_user(user_id):
    return Group.query.get(int(user_id))


# ======================
# コード生成
# ======================
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ======================
# ログイン
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form["group_code"]

        group = Group.query.filter_by(group_code=code).first()

        if group:
            login_user(group)

            # ★重要：セッション永続化
            return redirect(url_for("home"))

        return render_template("login.html", error="コードが違います")

    return render_template("login.html")


# ======================
# 団体作成
# ======================
@app.route("/create_group", methods=["GET", "POST"])
def create_group():
    if request.method == "POST":
        name = request.form["group_name"]
        code = generate_code()

        g = Group(group_name=name, group_code=code)
        db.session.add(g)
        db.session.commit()

        return render_template("create_group.html", code=code)

    return render_template("create_group.html", code=None)


# ======================
# ホーム
# ======================
@app.route("/home")
@login_required
def home():
    return render_template("home.html", group=current_user)


# ======================
# ログアウト
# ======================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ======================
# メンバー
# ======================
@app.route("/members", methods=["GET", "POST"])
@login_required
def members():
    if request.method == "POST":
        m = Member(
            group_id=current_user.id,
            name=request.form["name"],
            part=request.form["part"]
        )
        db.session.add(m)
        db.session.commit()

    members = Member.query.filter_by(group_id=current_user.id).all()
    return render_template("members.html", members=members)


@app.route("/delete_member/<int:id>")
@login_required
def delete_member(id):
    m = Member.query.filter_by(id=id, group_id=current_user.id).first()
    if m:
        db.session.delete(m)
        db.session.commit()
    return redirect("/members")


# ======================
# 個人反省
# ======================
@app.route("/add_reflection", methods=["GET", "POST"])
@login_required
def add_reflection():
    if request.method == "POST":
        r = Reflection(
            group_id=current_user.id,
            date=request.form["date"],
            name=request.form["name"],
            part=request.form["part"],
            reflection=request.form["reflection"]
        )
        db.session.add(r)
        db.session.commit()
        return redirect("/reflections")

    return render_template("add_reflection.html")


@app.route("/reflections")
@login_required
def reflections():
    rows = Reflection.query.filter_by(group_id=current_user.id)\
        .order_by(Reflection.date.desc()).all()
    return render_template("reflections.html", rows=rows)


@app.route("/edit_reflection/<int:id>", methods=["GET", "POST"])
@login_required
def edit_reflection(id):
    row = Reflection.query.filter_by(id=id, group_id=current_user.id).first()

    if request.method == "POST":
        if row:
            row.reflection = request.form["reflection"]
            db.session.commit()
        return redirect("/reflections")

    return render_template("edit_reflection.html", row=row)


@app.route("/delete_reflection/<int:id>")
@login_required
def delete_reflection(id):
    r = Reflection.query.filter_by(id=id, group_id=current_user.id).first()
    if r:
        db.session.delete(r)
        db.session.commit()
    return redirect("/reflections")


# ======================
# 全体反省
# ======================
@app.route("/add_group_reflection", methods=["GET", "POST"])
@login_required
def add_group_reflection():
    if request.method == "POST":
        g = GroupReflection(
            group_id=current_user.id,
            date=request.form["date"],
            reflection=request.form["reflection"]
        )
        db.session.add(g)
        db.session.commit()
        return redirect("/group_reflections")

    return render_template("add_group_reflection.html")


@app.route("/group_reflections")
@login_required
def group_reflections():
    rows = GroupReflection.query.filter_by(group_id=current_user.id)\
        .order_by(GroupReflection.date.desc()).all()

    return render_template("group_reflections.html", rows=rows)


# ======================
# パート反省
# ======================
@app.route("/add_part_reflection", methods=["GET", "POST"])
@login_required
def add_part_reflection():
    if request.method == "POST":
        p = PartReflection(
            group_id=current_user.id,
            date=request.form["date"],
            part=request.form["part"],
            reflection=request.form["reflection"]
        )
        db.session.add(p)
        db.session.commit()
        return redirect("/part_reflections")

    return render_template("add_part_reflection.html")


@app.route("/part_reflections")
@login_required
def part_reflections():
    rows = PartReflection.query.filter_by(group_id=current_user.id)\
        .order_by(PartReflection.date.desc()).all()

    return render_template("part_reflections.html", rows=rows)


# ======================
# 検索
# ======================
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = []

    if request.method == "POST":
        keyword = request.form["keyword"]

        results = Reflection.query.filter(
            Reflection.group_id == current_user.id,
            (
                Reflection.name.like(f"%{keyword}%") |
                Reflection.part.like(f"%{keyword}%") |
                Reflection.reflection.like(f"%{keyword}%") |
                Reflection.date.like(f"%{keyword}%")
            )
        ).all()

    return render_template("search.html", results=results)


# ======================
# 起動
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))