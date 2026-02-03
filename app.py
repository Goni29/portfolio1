from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import os
from dotenv import load_dotenv
from datetime import timedelta
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import check_password_hash

app = Flask(__name__)
@app.template_filter("mask_name")
def mask_name(name):
    if not name:
        return ""

    name = str(name)
    length = len(name)

    if length == 1:
        return name
    elif length == 2:
        return name[0] + "*"
    else:
        return name[0] + ("*" * (length - 2)) + name[-1]
@app.template_filter("mask_email")
def mask_email(email):
    if not email or "@" not in email:
        return ""

    email = str(email)
    local, domain = email.split("@", 1)
    length = len(local)

    if length <= 1:
        masked_local = local + "*"
    elif length == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[:2] + ("*" * (length - 2))

    return masked_local + "@" + domain
load_dotenv()

@app.template_filter("kst")
def kst(dt):
    if dt is None:
        return ""
    return (dt + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

# DB 설정

db_path = os.path.join(app.instance_path, "app.db")
os.makedirs(app.instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

db = SQLAlchemy(app)

import os

print("✅ 현재 작업 폴더:", os.getcwd())
print("✅ DB 절대 경로:", db_path)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"  # 로그인 안하면 여기로 이동

# 문의 모델
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="대기")
    password_hash = db.Column(db.String(255), nullable=True)
    answer = db.Column(db.Text, default="")
    answered_at = db.Column(db.DateTime, nullable=True)
class Admin(UserMixin):
    # 단일 관리자 계정만 쓰는 가장 쉬운 방식 (DB에 저장 안 함)
    id = "admin"

@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return Admin()
    return None

# 페이지 라우트
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/service")
def service():
    return redirect(url_for("about"))

@app.route("/contact")
def contact_info():
    page = request.args.get("page", "1")
    try:
        page = int(page)
    except ValueError:
        page = 1

    per_page = 5
    if page < 1:
        page = 1

    query = Contact.query.order_by(Contact.created_at.desc())
    total = query.count()
    contacts = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "contact_info.html",
        contacts=contacts,
        page=page,
        total_pages=total_pages,
        total=total,
    )

@app.route("/contact/new", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        pw = request.form["password"]
        new_contact = Contact(
            name=request.form['name'],
            email=request.form['email'],
            message=request.form['message'],
            password_hash=generate_password_hash(pw)
        )
        db.session.add(new_contact)
        db.session.commit()

        flash(f"문의가 접수되었습니다. 문의번호는 {new_contact.id} 입니다. (비밀번호로 조회 가능)")
        return redirect(url_for('contact_info'))

    return render_template("contact_form.html")

@app.route("/contact/<int:contact_id>")
def contact_password(contact_id):
    c = Contact.query.get_or_404(contact_id)
    return render_template("contact_password.html", c=c)

@app.route("/contact/<int:contact_id>/view", methods=["POST"])
def contact_view_post(contact_id):
    c = Contact.query.get_or_404(contact_id)
    password = request.form.get("password", "")

    if not c.password_hash:
        flash("이 문의는 비밀번호가 설정되어 있지 않습니다.")
        return redirect(url_for("contact_password", contact_id=contact_id))

    if not check_password_hash(c.password_hash, password):
        flash("비밀번호가 올바르지 않습니다.")
        return redirect(url_for("contact_password", contact_id=contact_id))

    return render_template("contact_my_detail.html", c=c)

@app.route("/admin/contacts")
@login_required
def admin_contacts():
    # query params
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()  # "", "대기", "처리중", "완료"
    page = request.args.get("page", "1")
    try:
        page = int(page)
    except ValueError:
        page = 1

    per_page = 10
    if page < 1:
        page = 1

    # 정렬: 대기 -> 처리중 -> 완료 -> 기타, 그 안에서 최신순
    status_order = db.case(
        (Contact.status == "대기", 1),
        (Contact.status == "처리중", 2),
        (Contact.status == "완료", 3),
        else_=4
    )

    query = Contact.query

    # 상태 필터
    if status in ["대기", "처리중", "완료"]:
        query = query.filter(Contact.status == status)

    # 검색(이름/이메일/내용)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Contact.name.ilike(like),
            Contact.email.ilike(like),
            Contact.message.ilike(like),
        ))

    total = query.count()
    contacts = (query
                .order_by(status_order, Contact.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all())

    total_pages = (total + per_page - 1) // per_page

    pending_count = Contact.query.filter(Contact.status != "완료").count()

    return render_template(
        "admin/contacts.html",
        contacts=contacts,
        q=q,
        status=status,
        page=page,
        total_pages=total_pages,
        total=total,
        pending_count=pending_count
    )

@app.route("/admin/contacts/<int:contact_id>")
@login_required
def admin_contact_detail(contact_id):
    c = Contact.query.get_or_404(contact_id)
    return render_template("admin/contact_detail.html", c=c)

@app.route("/adminlogin/loginrhksflwk-9x2k", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            login_user(Admin())
            return redirect(url_for("admin_contacts"))
        else:
            flash("아이디 또는 비밀번호가 틀렸습니다.")

    return render_template("admin/login.html")

@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))

@app.route("/admin/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def admin_contact_delete(contact_id):
    c = Contact.query.get_or_404(contact_id)
    db.session.delete(c)
    db.session.commit()
    flash("삭제 완료")
    return redirect(url_for("admin_contacts"))

@app.route("/admin/contacts/<int:contact_id>/status", methods=["POST"])
@login_required
def admin_contact_status(contact_id):
    c = Contact.query.get_or_404(contact_id)
    new_status = request.form.get("status")

    if new_status in ["대기", "처리중", "완료"]:
        c.status = new_status
        db.session.commit()
        flash("상태가 변경되었습니다.")
    else:
        flash("잘못된 상태값입니다.")

    return redirect(url_for("admin_contacts"))

@app.route("/admin/contacts/<int:contact_id>/answer", methods=["POST"])
@login_required
def admin_contact_answer(contact_id):
    c = Contact.query.get_or_404(contact_id)
    answer = request.form.get("answer", "").strip()

    c.answer = answer
    c.answered_at = datetime.utcnow() if answer else None

    if answer:
        c.status = "완료"

    db.session.commit()
    flash("답변이 저장되었습니다.")
    return redirect(url_for("admin_contact_detail", contact_id=contact_id))

# if __name__ == "__main__":
#     with app.app_context():
#         db.create_all()  # DB 테이블 생성
#     app.run(debug=True)
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()