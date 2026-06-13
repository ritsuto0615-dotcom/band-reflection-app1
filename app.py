from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
import random
import string
import os
from functools import wraps

app = Flask(__name__)

app.config["SECRET_KEY"] = "band_app_jwt_super_secret_2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ======================
# 設定
# ======================
app.config["SECRET_KEY"] = "band_app_jwt_super_secret_2026"

db = SQLAlchemy(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ======================
# モデル（変更なし）
# ======================
class Group(db.Model):
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


with app.app_context():
    db.create_all()


# ======================
# JWT生成
# ======================
def create_token(group_id):
    payload = {
        "group_id": group_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


# ======================
# JWT認証デコレータ
# ======================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("token")

        if not token:
            return redirect(url_for("login"))

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            group = Group.query.get(data["group_id"])
        except:
            return redirect(url_for("login"))

        if not group:
            return redirect(url_for("login"))

        return f(group, *args, **kwargs)

    return decorated


# ======================
# コード生成
# ======================
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ======================
# ログイン（JWT化）
# ======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form["group_code"]

        group = Group.query.filter_by(group_code=code).first()

        if group:
            token = create_token(group.id)

            resp = make_response(redirect(url_for("home")))
            resp.set_cookie("token", token, httponly=True, max_age=7*24*60*60)

            return resp

        return render_template("login.html", error="コードが違います")

    return render_template("login.html")


# ======================
# ホーム
# ======================
@app.route("/home")
@token_required
def home(group):
    return render_template("home.html", group=group)


# ======================
# ログアウト
# ======================
@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("token")
    return resp


# ======================
# メンバー
# ======================
@app.route("/members", methods=["GET", "POST"])
@token_required
def members(group):
    if request.method == "POST":
        m = Member(
            group_id=group.id,
            name=request.form["name"],
            part=request.form["part"]
        )
        db.session.add(m)
        db.session.commit()

    members = Member.query.filter_by(group_id=group.id).all()
    return render_template("members.html", members=members)


# ======================
# メンバー削除
# ======================
@app.route("/delete_member/<int:id>")
@token_required
def delete_member(group, id):
    m = Member.query.filter_by(id=id, group_id=group.id).first()
    if m:
        db.session.delete(m)
        db.session.commit()
    return redirect("/members")


# ======================
# 個人反省
# ======================
@app.route("/add_reflection", methods=["GET", "POST"])
@token_required
def add_reflection(group):
    if request.method == "POST":
        r = Reflection(
            group_id=group.id,
            date=request.form["date"],
            name=request.form["name"],
            part=request.form["part"],
            reflection=request.form["reflection"]
        )
        db.session.add(r)
        db.session.commit()
        return redirect("/reflections")

    return render_template("add_reflection.html")


# ======================
# 一覧
# ======================
@app.route("/reflections")
@token_required
def reflections(group):
    rows = Reflection.query.filter_by(group_id=group.id)\
        .order_by(Reflection.date.desc()).all()

    return render_template("reflections.html", rows=rows)


# ======================
# 編集
# ======================
@app.route("/edit_reflection/<int:id>", methods=["GET", "POST"])
@token_required
def edit_reflection(group, id):
    row = Reflection.query.filter_by(id=id, group_id=group.id).first()

    if request.method == "POST":
        if row:
            row.reflection = request.form["reflection"]
            db.session.commit()
        return redirect("/reflections")

    return render_template("edit_reflection.html", row=row)


# ======================
# 削除
# ======================
@app.route("/delete_reflection/<int:id>")
@token_required
def delete_reflection(group, id):
    r = Reflection.query.filter_by(id=id, group_id=group.id).first()
    if r:
        db.session.delete(r)
        db.session.commit()
    return redirect("/reflections")


# ======================
# 全体反省
# ======================
@app.route("/add_group_reflection", methods=["GET", "POST"])
@token_required
def add_group_reflection(group):
    if request.method == "POST":
        g = GroupReflection(
            group_id=group.id,
            date=request.form["date"],
            reflection=request.form["reflection"]
        )
        db.session.add(g)
        db.session.commit()
        return redirect("/group_reflections")

    return render_template("add_group_reflection.html")


@app.route("/group_reflections")
@token_required
def group_reflections(group):
    rows = GroupReflection.query.filter_by(group_id=group.id)\
        .order_by(GroupReflection.date.desc()).all()

    return render_template("group_reflections.html", rows=rows)


# ======================
# パート反省
# ======================
@app.route("/add_part_reflection", methods=["GET", "POST"])
@token_required
def add_part_reflection(group):
    if request.method == "POST":
        p = PartReflection(
            group_id=group.id,
            date=request.form["date"],
            part=request.form["part"],
            reflection=request.form["reflection"]
        )
        db.session.add(p)
        db.session.commit()
        return redirect("/part_reflections")

    return render_template("add_part_reflection.html")


@app.route("/part_reflections")
@token_required
def part_reflections(group):
    rows = PartReflection.query.filter_by(group_id=group.id)\
        .order_by(PartReflection.date.desc()).all()

    return render_template("part_reflections.html", rows=rows)


# ======================
# 検索
# ======================
@app.route("/search", methods=["GET", "POST"])
@token_required
def search(group):
    results = []

    if request.method == "POST":
        keyword = request.form["keyword"]

        results = Reflection.query.filter(
            Reflection.group_id == group.id,
            (
                Reflection.name.like(f"%{keyword}%") |
                Reflection.part.like(f"%{keyword}%") |
                Reflection.reflection.like(f"%{keyword}%") |
                Reflection.date.like(f"%{keyword}%")
            )
        ).all()

    return render_template("search.html", results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))