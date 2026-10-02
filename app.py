import os
import webbrowser
import urllib.parse
from threading import Timer
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key configuration for sessions
app.secret_key = os.environ.get("SECRET_KEY", "apnasevak_hyperlocal_secure_key_2026")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# Database Configuration (Supabase PostgreSQL / SQLite fallback)
database_url = os.environ.get("DATABASE_URL", "sqlite:///apnasevak.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# DUAL-LANGUAGE LOCALIZATION DICTIONARY
TRANSLATIONS = {
    "hi": {
        "brand_name": "अपनासेवक",
        "brand_tagline": "घर बैठे प्रमाणित एवं विश्वसनीय सेवाएं",
        "network_tag": "सत्यापित हाइपरलोकल नेटवर्क",
        "rating_text": "4.9 रेटिंग",
        "dispatch_text": "त्वरित सेवा"
    },
    "en": {
        "brand_name": "ApnaSevak",
        "brand_tagline": "Verified & Trusted Home Services at Your Doorstep",
        "network_tag": "Verified Hyperlocal Network",
        "rating_text": "4.9 Rating",
        "dispatch_text": "Quick Dispatch"
    }
}

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")  # customer, sevak, admin
    service_type = db.Column(db.String(100), nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    sevak_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(50), default="Pending")  # Pending, Accepted, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Context processor for templates
@app.context_processor
def inject_translations():
    lang = session.get("lang", "hi")
    return {
        "lang": lang,
        "t": TRANSLATIONS.get(lang, TRANSLATIONS["hi"])
    }

# --- ROUTES ---
@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ["hi", "en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

@app.route("/")
@app.route("/home")
def index():
    sevaks = User.query.filter_by(role="sevak", is_available=True).all()
    return render_template("index.html", sevaks=sevaks)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "customer")
        service_type = request.form.get("service_type", "").strip()

        if not name or not phone or not password:
            flash("Kripya sabhi fields bharein.", "error")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(phone=phone).first()
        if existing_user:
            flash("Yeh phone number pehle se registered hai.", "error")
            return redirect(url_for("login"))

        new_user = User(
            name=name,
            phone=phone,
            password_hash=generate_password_hash(password),
            role=role,
            service_type=service_type if role == "sevak" else None
        )
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        session["user_name"] = new_user.name
        session["user_role"] = new_user.role
        flash("Registration safal raha!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = user.role
            flash(f"Swagat hai, {user.name}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Galat phone number ya password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Aap safaltapurvak log out ho chuke hain.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    if user.role == "sevak":
        orders = Booking.query.filter((Booking.sevak_id == user.id) | (Booking.sevak_id == None)).order_by(Booking.id.desc()).all()
    elif user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    else:
        orders = Booking.query.filter_by(customer_id=user.id).order_by(Booking.id.desc()).all()

    return render_template("dashboard.html", user=user, orders=orders)

@app.route("/gateway", methods=["GET", "POST"])
def gateway():
    service = request.args.get("service", "General Service")
    if request.method == "POST":
        customer_name = request.form.get("name", "").strip()
        customer_phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        service_name = request.form.get("service", service)

        new_booking = Booking(
            customer_id=session.get("user_id"),
            customer_name=customer_name,
            customer_phone=customer_phone,
            address=address,
            service_name=service_name,
            status="Pending"
        )
        db.session.add(new_booking)
        db.session.commit()
        flash("Aapka order successfully book ho gaya hai!", "success")
        return redirect(url_for("dashboard") if "user_id" in session else url_for("index"))

    return render_template("gateway.html", service=service)

@app.route("/update_order_status/<int:order_id>/<status>")
def update_order_status(order_id, status):
    if "user_id" not in session:
        return redirect(url_for("login"))

    booking = Booking.query.get_or_404(order_id)
    user_id = session["user_id"]

    if status == "accept":
        booking.sevak_id = user_id
        booking.status = "Accepted"
    elif status == "complete":
        booking.status = "Completed"
    elif status == "cancel":
        booking.status = "Cancelled"

    db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/admin_dashboard")
def admin_dashboard():
    try:
        all_users = User.query.all()
    except Exception:
        all_users = []

    try:
        all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    except Exception:
        all_bookings = []

    return render_template("admin_dashboard.html", users=all_users, bookings=all_bookings)

# Default Sample Sevaks if database is fresh/empty
def seed_default_services():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="sevak").first():
            demo_sevaks = [
                User(name="Ramesh Kumar", phone="9876543210", password_hash=generate_password_hash("123456"), role="sevak", service_type="Electrician", is_available=True),
                User(name="Suresh Sharma", phone="9876543211", password_hash=generate_password_hash("123456"), role="sevak", service_type="Plumber", is_available=True),
                User(name="Amit Verma", phone="9876543212", password_hash=generate_password_hash("123456"), role="sevak", service_type="Carpenter", is_available=True),
                User(name="Pooja Devi", phone="9876543213", password_hash=generate_password_hash("123456"), role="sevak", service_type="Cleaning", is_available=True),
                User(name="Admin", phone="9999999999", password_hash=generate_password_hash("admin123"), role="admin", is_available=True)
            ]
            db.session.add_all(demo_sevaks)
            db.session.commit()

if __name__ == "__main__":
    seed_default_services()
    app.run(debug=True, host="0.0.0.0", port=5000)