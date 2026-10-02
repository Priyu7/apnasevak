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

# ----------------- DUAL-LANGUAGE LOCALIZATION DICTIONARY -----------------
TRANSLATIONS = {
    "hi": {
        "brand_name": "अपनासेवक",
        "brand_tagline": "घर बैठे प्रमाणित एवं विश्वसनीय सेवाएं",
        "network_tag": "सत्यापित हाइपरलोकल नेटवर्क",
        "rating_text": "4.9 रेटिंग",
        "dispatch_text": "त्वरित सेवा",
        "select_language_prompt": "भाषा चुनें",
        "customer_tab": "ग्राहक (Customer)",
        "sevak_tab": "सेवक पार्टनर",
        "welcome": "अपनासेवक में आपका स्वागत है",
        "login": "लॉग इन करें",
        "signup": "नया खाता बनाएं",
        "services": "सेवाएं",
        "orders": "मेरे ऑर्डर",
        "requests": "अनुरोध केरल",
        "logout": "लॉग आउट",
        "owner_console": "स्वामी नियंत्रण कक्ष",
        "view_experts": "विशेषज्ञ देखें और चुनें",
        "call": "कॉल करें",
        "whatsapp": "व्हाट्सएप",
        "accept": "स्वीकार करें",
        "reject": "अस्वीकार करें",
        "complete": "पूर्ण घोषित करें",
    },
    "en": {
        "brand_name": "ApnaSevak",
        "brand_tagline": "Certified & Reliable Home Services at Your Doorstep",
        "network_tag": "Verified Hyperlocal Network",
        "rating_text": "4.9 Rating",
        "dispatch_text": "Instant Dispatch",
        "select_language_prompt": "Select Language",
        "customer_tab": "Customer",
        "sevak_tab": "Sevak Partner",
        "welcome": "Welcome to ApnaSevak",
        "login": "Login",
        "signup": "Sign Up",
        "services": "Services",
        "orders": "My Orders",
        "requests": "Service Requests",
        "logout": "Logout",
        "owner_console": "Owner Console",
        "view_experts": "View & Select Experts",
        "call": "Call Now",
        "whatsapp": "WhatsApp",
        "accept": "Accept",
        "reject": "Decline",
        "complete": "Mark Completed",
    }
}

# ----------------- DATABASE MODELS -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="customer")  # customer, sevak, admin
    service_type = db.Column(db.String(100), nullable=True) # For sevaks: Electrician, Plumber, etc.
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sevak_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    service_name = db.Column(db.String(120), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    preferred_time = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default="Pending") # Pending, Accepted, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_bookings')
    sevak = db.relationship('User', foreign_keys=[sevak_id], backref='sevak_tasks')

with app.app_context():
    db.create_all()

# ----------------- WHATSAPP UTILITY HELPER -----------------
def generate_whatsapp_link(phone, customer_name, service_name, address, preferred_time):
    clean_phone = "".join(filter(str.isdigit, str(phone)))
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    
    msg = (
        f"Namaste {customer_name}! 🙏\n"
        f"ApnaSevak par aapka order praapt ho gaya hai:\n\n"
        f"🛠️ *Seva:* {service_name}\n"
        f"📅 *Samay:* {preferred_time}\n"
        f"📍 *Pata:* {address}\n\n"
        f"Aapki seva ke liye hum jald hi confirm karenge. Dhanyawad!"
    )
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

# ----------------- TEMPLATE CONTEXT PROCESSOR -----------------
@app.context_processor
def inject_translations():
    lang = session.get("lang", "hi")
    return dict(t=TRANSLATIONS.get(lang, TRANSLATIONS["hi"]), current_lang=lang)

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ["hi", "en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

# ----------------- ROUTES -----------------
@app.route("/")
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

        if new_user.role == "sevak":
            return redirect(url_for("sevak_dashboard"))
        elif new_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
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

            if user.role == "sevak":
                return redirect(url_for("sevak_dashboard"))
            elif user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))
        
        flash("Galat phone number ya password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    orders = Booking.query.filter_by(customer_id=user_id).order_by(Booking.id.desc()).all()
    
    # Generate WhatsApp URL for each order
    for o in orders:
        o.wa_link = generate_whatsapp_link(o.customer_phone, o.customer_name, o.service_name, o.address, o.preferred_time)

    return render_template("dashboard.html", orders=orders)

@app.route("/book", methods=["POST"])
def book_service():
    user_id = session.get("user_id")
    if not user_id:
        flash("Booking karne ke liye login karein.", "warning")
        return redirect(url_for("login"))

    service_name = request.form.get("service_name", "General Service")
    customer_name = request.form.get("customer_name") or session.get("user_name")
    customer_phone = request.form.get("customer_phone")
    address = request.form.get("address")
    preferred_time = request.form.get("preferred_time", "Jald se jald (ASAP)")
    sevak_id = request.form.get("sevak_id")

    booking = Booking(
        customer_id=user_id,
        sevak_id=int(sevak_id) if sevak_id else None,
        service_name=service_name,
        customer_name=customer_name,
        customer_phone=customer_phone,
        address=address,
        preferred_time=preferred_time,
        status="Pending"
    )
    db.session.add(booking)
    db.session.commit()

    # Generate instant WhatsApp redirect URL
    wa_url = generate_whatsapp_link(customer_phone, customer_name, service_name, address, preferred_time)
    session["last_whatsapp_url"] = wa_url

    flash("Booking safaltapoorvak ho gayi!", "success")
    return redirect(url_for("dashboard"))

@app.route("/sevak_dashboard")
def sevak_dashboard():
    user_id = session.get("user_id")
    if not user_id or session.get("user_role") != "sevak":
        return redirect(url_for("login"))

    assigned_orders = Booking.query.filter_by(sevak_id=user_id).order_by(Booking.id.desc()).all()
    open_requests = Booking.query.filter_by(status="Pending", sevak_id=None).order_by(Booking.id.desc()).all()
    
    # WhatsApp links for contacting customers directly
    for item in assigned_orders + open_requests:
        item.wa_link = generate_whatsapp_link(item.customer_phone, item.customer_name, item.service_name, item.address, item.preferred_time)

    return render_template("sevak_list.html", assigned=assigned_orders, open_reqs=open_requests)

@app.route("/update_order_status/<int:order_id>/<status>")
def update_order_status(order_id, status):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    booking = Booking.query.get_or_404(order_id)
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
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    all_users = User.query.all()
    all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template("admin_dashboard.html", users=all_users, bookings=all_bookings)

if __name__ == "__main__":
    # Local development run
    app.run(debug=True, host="0.0.0.0", port=5000)