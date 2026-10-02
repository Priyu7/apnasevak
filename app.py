import os
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
# Secret key configuration for sessions
app.secret_key = os.environ.get("SECRET_KEY", "apnasevak_hyperlocal_secure_key_2026")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///apnasevak.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

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
        "requests": "अनुरोध कंसोल",
        "logout": "लॉग आउट",
        "owner_console": "👑 स्वामी नियंत्रण कक्ष",
        "view_experts": "विशेषज्ञ देखें और चुनें →",
        "call": "कॉल करें",
        "whatsapp": "व्हाट्सएप",
        "accept": "स्वीकार करें",
        "reject": "अस्वीकार करें",
        "complete": "पूर्ण घोषित करें",
        "switch_lang": "English",
        "lang_code": "en"
    },
    "en": {
        "brand_name": "ApnaSevak",
        "brand_tagline": "Doorstep Home & Wellness Services",
        "network_tag": "Verified Hyperlocal Network",
        "rating_text": "4.9 Rating",
        "dispatch_text": "Express Dispatch",
        "select_language_prompt": "Choose Language",
        "customer_tab": "Customer",
        "sevak_tab": "Sevak Partner",
        "welcome": "Welcome to ApnaSevak",
        "login": "Sign In",
        "signup": "Sign Up",
        "services": "Services",
        "orders": "My Orders",
        "requests": "Requests Console",
        "logout": "Logout",
        "owner_console": "👑 Owner Console",
        "view_experts": "View Experts & Choose →",
        "call": "Call",
        "whatsapp": "WhatsApp",
        "accept": "Accept",
        "reject": "Reject",
        "complete": "Mark Completed",
        "switch_lang": "हिन्दी",
        "lang_code": "hi"
    }
}

@app.context_processor
def inject_lang():
    lang = session.get("lang", "en")
    return {"t": TRANSLATIONS.get(lang, TRANSLATIONS["en"]), "current_lang": lang}

@app.route("/set-lang/<lang_code>")
def set_language(lang_code):
    if lang_code in ["hi", "en"]:
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("gateway"))

# ----------------- DATABASE MODELS -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'customer', 'provider', 'admin'
    skill_key = db.Column(db.String(50), nullable=True)
    rating = db.Column(db.String(10), default="5.0")
    rating_count = db.Column(db.Integer, default=1)
    experience = db.Column(db.String(20), default="3+ Yrs")
    password = db.Column(db.String(200), nullable=False)

    bookings = db.relationship("Booking", backref="customer", foreign_keys="Booking.user_id", lazy=True)
    reviews_received = db.relationship("Review", backref="provider", foreign_keys="Review.provider_id", lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_title = db.Column(db.String(100), nullable=False)
    selected_tasks = db.Column(db.String(250), default="Standard Service")
    price = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="Pending")  # 'Pending', 'Accepted', 'Completed', 'Rejected'

    # Payment Tracking Fields
    payment_method = db.Column(db.String(50), default="Cash on Delivery")
    payment_status = db.Column(db.String(50), default="Pending")  # 'Pending', 'Paid'

    address = db.Column(db.String(300), nullable=False, default="Address not provided")
    landmark = db.Column(db.String(150), nullable=True)
    booking_date = db.Column(db.String(50), nullable=False, default="Today")
    time_slot = db.Column(db.String(50), nullable=False, default="Standard Slot")

    is_reviewed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    provider = db.relationship("User", foreign_keys=[provider_id])

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    customer = db.relationship("User", foreign_keys=[user_id])
    booking = db.relationship("Booking", foreign_keys=[booking_id])

# ----------------- SERVICES CATALOG -----------------
SERVICES_CATALOG = [
    {
        "key": "electrician",
        "price": "₹ 199",
        "en": {
            "title": "Electrician",
            "category": "Repairs",
            "desc": "Switchboard, fan fitting, wiring inspection & electrical appliance fix",
            "tasks": ["Switchboard Repair", "Ceiling Fan Fitting", "MCB / Fuse Repair", "Inverter Wiring", "Light / Chandelier Installation"]
        },
        "hi": {
            "title": "इलेक्ट्रीशियन (विद्युत सेवा)",
            "category": "मरम्मत",
            "desc": "स्विचबोर्ड, पंखा संस्थापन, संपूर्ण वायरिंग परीक्षण एवं घरेलू उपकरण सुधार",
            "tasks": ["स्विचबोर्ड मरम्मत", "सीलिंग फैन फिटिंग", "एमसीबी / फ्यूज सुधार", "इन्वर्टर वायरिंग", "झूमर / लाइट फिटिंग"]
        }
    },
    {
        "key": "plumber",
        "price": "₹ 249",
        "en": {
            "title": "Plumber",
            "category": "Repairs",
            "desc": "Tap leakage, wash basin fitting, pipeline repair & flush tank fix",
            "tasks": ["Tap Leakage Fix", "Wash Basin Fitting", "Toilet Flush Tank Repair", "Water Tank Cleaning", "Pipeline Blockage Clear"]
        },
        "hi": {
            "title": "प्लम्बर (जल आपूर्ति कारीगर)",
            "category": "मरम्मत",
            "desc": "नल का रिसाव, वॉश बेसिन फिटिंग, पाइपलाइन मरम्मत व फ्लश टैंक समाधान",
            "tasks": ["नल रिसाव मरम्मत", "वॉश बेसिन फिटिंग", "फ्लश टैंक सुधार", "पानी टंकी सफाई", "पाइपलाइन रुकावट निकासी"]
        }
    },
    {
        "key": "carpenter",
        "price": "₹ 299",
        "en": {
            "title": "Carpenter",
            "category": "Repairs",
            "desc": "Furniture assembly, drawer channel, door locks & latch repair",
            "tasks": ["Door Lock Fitting", "Bed Assembly / Repair", "Drawer Channel Fix", "Curtain Rod Fitting", "Door Hinges Alignment"]
        },
        "hi": {
            "title": "कारपेंटर (बढ़ई कार्य)",
            "category": "मरम्मत",
            "desc": "फर्नीचर संयोजन, दराज चैनल, दरवाजों के ताले व कुंडी मरम्मत",
            "tasks": ["दरवाजे के ताले की फिटिंग", "बेड / दीवान संयोजन", "दराज चैनल सुधार", "पर्दा रॉड फिटिंग", "कब्जे संरेखण"]
        }
    },
    {
        "key": "ac_repair",
        "price": "₹ 499",
        "en": {
            "title": "AC Repair & Servicing",
            "category": "Appliances",
            "desc": "Powerjet filter deep cleaning, gas refill & cooling diagnostics",
            "tasks": ["Powerjet Deep Servicing", "Gas Leakage & Refilling", "PCB Board Repair", "Water Leakage Fix", "Installation / Uninstallation"]
        },
        "hi": {
            "title": "एसी मरम्मत एवं सर्विसिंग",
            "category": "उपकरण",
            "desc": "पावरजेट फिल्टर सर्विसिंग, गैस रिफिलिंग एवं शीतलन समस्या निवारण",
            "tasks": ["पावरजेट सघन सर्विसिंग", "गैस लीकेज व रिफिलिंग", "पीसीबी बोर्ड मरम्मत", "पानी रिसाव समाधान", "स्थापना / निष्कासन"]
        }
    },
    {
        "key": "salon",
        "price": "₹ 599",
        "en": {
            "title": "Ladies Beauty & Salon",
            "category": "Salon",
            "desc": "Doorstep waxing, threading, facial, hair spa & manicure",
            "tasks": ["Full Body Waxing", "Gold / Fruit Facial", "Eyebrow Threading", "Hair Spa & Trimming", "Pedicure & Manicure"]
        },
        "hi": {
            "title": "महिला सौंदर्य एवं सैलून",
            "category": "सौंदर्य",
            "desc": "घर पर वैक्सिंग, थ्रेडिंग, फेशियल, हेयर स्पा, मैनीक्योर व पैडीक्योर",
            "tasks": ["वैक्सिंग सेवा", "गोल्ड / फ्रूट फेशियल", "आइब्रो थ्रेडिंग", "हेयर स्पा एवं ट्रिमिंग", "पैडीक्योर व मैनीक्योर"]
        }
    },
    {
        "key": "massage_men",
        "price": "₹ 899",
        "en": {
            "title": "Full Body Massage (Men)",
            "category": "Spa",
            "desc": "Deep tissue relaxation therapy, lower back pain relief & aroma oil massage",
            "tasks": ["Swedish Deep Tissue Massage", "Head, Neck & Shoulder Therapy", "Lower Back Pain Relief", "Aroma Essential Oil Therapy"]
        },
        "hi": {
            "title": "फुल बॉडी मसाज (पुरुष)",
            "category": "स्पा",
            "desc": "तनाव निवारक डीप टिशू मसाज, कमर दर्द से राहत एवं सुगंधित तेल मालिश",
            "tasks": ["स्वीडिश डीप टिशू मालिश", "सिर, गर्दन व कंधा मालिश", "पीठ एवं कमर दर्द राहत", "एरोमा थेरेपी"]
        }
    },
    {
        "key": "spa_women",
        "price": "₹ 999",
        "en": {
            "title": "Relaxing Body Spa (Women)",
            "category": "Spa",
            "desc": "Stress relief Ayurvedic potli therapy, hot oil massage & foot reflexology",
            "tasks": ["Full Body Stress Relief Spa", "Ayurvedic Potli Therapy", "Foot Reflexology", "Head Massage & Hair Pack"]
        },
        "hi": {
            "title": "रिलैक्सिंग बॉडी स्पा (महिलाएं)",
            "category": "स्पा",
            "desc": "तनाव मुक्ति आयुर्वेदिक पोटली थेरेपी, हॉट ऑयल मसाज व पाद प्रक्षालन",
            "tasks": ["फुल बॉडी तनाव राहत स्पा", "आयुर्वेदिक पोटली थेरेपी", "फुट रिफ्लेक्सोलॉजी", "हेड मसाज व हेयर पैक"]
        }
    },
    {
        "key": "cleaning",
        "price": "₹ 1199",
        "en": {
            "title": "Deep Home Cleaning",
            "category": "Cleaning",
            "desc": "Machine floor scrubbing, kitchen degreasing, sofa vacuuming & bathroom sanitation",
            "tasks": ["Bathroom Deep Sanitization", "Kitchen Chimney & Tile Degreasing", "Floor Machine Scrubbing", "Sofa Vacuum & Shampoo", "Balcony Cleaning"]
        },
        "hi": {
            "title": "घर की गहन सफाई (डीप क्लीनिंग)",
            "category": "सफाई",
            "desc": "मशीन द्वारा फर्श स्क्रबिंग, रसोई डिग्रेसिंग, सोफा शैम्पू व बाथरूम सैनिटाइजेशन",
            "tasks": ["बाथरूम डीप सैनिटाइजेशन", "रसोई चिमनी व टाइल सफाई", "फर्श मशीन स्क्रबिंग", "सोफा वैक्यूम व शैम्पू", "बालकनी सफाई"]
        }
    }
]

def get_localized_services(lang):
    localized = []
    for s in SERVICES_CATALOG:
        info = s.get(lang, s["en"])
        localized.append({
            "key": s["key"],
            "title": info["title"],
            "category": info["category"],
            "desc": info["desc"],
            "price": s["price"],
            "tasks": info["tasks"]
        })
    return localized

def seed_providers():
    # Admin User Seed
    if not User.query.filter_by(role="admin").first():
        owner = User(
            name="Platform Owner",
            phone="9999999999",
            email="owner@apnasevak.com",
            role="admin",
            password=generate_password_hash("admin123")
        )
        db.session.add(owner)
        db.session.commit()

    # Providers Seed
    if not User.query.filter_by(role="provider").first():
        sample_sevaks = [
            User(name="Ramesh Sharma", phone="9876543211", email="ramesh@sevak.com", role="provider", skill_key="electrician", rating="4.9", rating_count=18, experience="5+ Yrs", password=generate_password_hash("1234")),
            User(name="Sunil Verma", phone="9876543212", email="sunil@sevak.com", role="provider", skill_key="electrician", rating="4.7", rating_count=12, experience="3+ Yrs", password=generate_password_hash("1234")),
            User(name="Mohan Lal", phone="9876543213", email="mohan@sevak.com", role="provider", skill_key="plumber", rating="4.8", rating_count=14, experience="6+ Yrs", password=generate_password_hash("1234")),
            User(name="Pooja Sen", phone="9876543216", email="pooja@sevak.com", role="provider", skill_key="salon", rating="5.0", rating_count=25, experience="4+ Yrs", password=generate_password_hash("1234")),
            User(name="Anil Rawat", phone="9876543218", email="anil@sevak.com", role="provider", skill_key="massage_men", rating="4.9", rating_count=20, experience="6+ Yrs", password=generate_password_hash("1234")),
            User(name="Karan Yadav", phone="9876543220", email="karan@sevak.com", role="provider", skill_key="cleaning", rating="4.7", rating_count=9, experience="4+ Yrs", password=generate_password_hash("1234"))
        ]
        db.session.add_all(sample_sevaks)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_providers()

# ----------------- ROUTING & WORKFLOW LOGIC -----------------
@app.route("/")
def gateway():
    if "user_id" in session:
        role = session.get("user_role")
        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif role == "provider":
            return redirect(url_for("dashboard"))
        return redirect(url_for("home"))
    return render_template("gateway.html")

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("gateway"))
    if session.get("user_role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if session.get("user_role") == "provider":
        return redirect(url_for("dashboard"))

    lang = session.get("lang", "en")
    services = get_localized_services(lang)

    query = request.args.get("q", "").strip().lower()
    if query:
        services = [s for s in services if query in s["title"].lower() or query in s["category"].lower()]

    return render_template("index.html", services=services, search_query=query)

@app.route("/service/<service_key>/providers")
def service_providers(service_key):
    if "user_id" not in session:
        return redirect(url_for("gateway"))
    if session.get("user_role") in ["provider", "admin"]:
        return redirect(url_for("dashboard"))

    lang = session.get("lang", "en")
    all_localized = get_localized_services(lang)
    service_obj = next((s for s in all_localized if s["key"] == service_key), all_localized[0])

    sevaks = User.query.filter_by(role="provider", skill_key=service_key).all()
    if not sevaks:
        sevaks = User.query.filter_by(role="provider").limit(4).all()

    return render_template("sevak_list.html", service=service_obj, sevaks=sevaks, service_key=service_key)

@app.route("/book/confirm/<int:provider_id>", methods=["POST"])
def confirm_booking(provider_id):
    if "user_id" not in session:
        return redirect(url_for("gateway"))
    if session.get("user_role") in ["provider", "admin"]:
        return redirect(url_for("dashboard"))

    service_title = request.form.get("service_title")
    price = request.form.get("price")
    selected_tasks_list = request.form.getlist("tasks")
    tasks_string = ", ".join(selected_tasks_list) if selected_tasks_list else "General Service"

    address = request.form.get("address", "").strip()
    landmark = request.form.get("landmark", "").strip()
    booking_date = request.form.get("booking_date", "").strip()
    time_slot = request.form.get("time_slot", "").strip()
    payment_method = request.form.get("payment_method", "Cash on Delivery")

    new_booking = Booking(
        service_title=service_title,
        selected_tasks=tasks_string,
        price=price,
        address=address,
        landmark=landmark,
        booking_date=booking_date,
        time_slot=time_slot,
        payment_method=payment_method,
        payment_status="Pending",
        user_id=int(session["user_id"]),
        provider_id=int(provider_id),
        status="Pending"
    )
    db.session.add(new_booking)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/booking/pay/<int:booking_id>", methods=["POST"])
def complete_payment(booking_id):
    if "user_id" not in session:
        return redirect(url_for("gateway"))
    
    booking = Booking.query.get_or_404(booking_id)
    method = request.form.get("payment_method", "UPI")
    
    booking.payment_method = method
    booking.payment_status = "Paid"
    db.session.commit()
    
    return redirect(url_for("dashboard"))

@app.route("/booking/review/<int:booking_id>", methods=["POST"])
def submit_review(booking_id):
    if "user_id" not in session or session.get("user_role") != "customer":
        return redirect(url_for("gateway"))

    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != int(session["user_id"]) or booking.status != "Completed":
        return redirect(url_for("dashboard"))

    rating_value = int(request.form.get("rating", 5))
    comment_text = request.form.get("comment", "").strip()

    new_review = Review(
        rating=rating_value,
        comment=comment_text,
        booking_id=booking.id,
        user_id=int(session["user_id"]),
        provider_id=booking.provider_id
    )
    booking.is_reviewed = True

    provider = User.query.get(booking.provider_id)
    all_prev_reviews = Review.query.filter_by(provider_id=provider.id).all()
    total_ratings = [r.rating for r in all_prev_reviews] + [rating_value]

    provider.rating_count = len(total_ratings)
    provider.rating = f"{(sum(total_ratings) / len(total_ratings)):.1f}"

    db.session.add(new_review)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    preselected_role = request.args.get("role", "customer")
    lang = session.get("lang", "en")
    services = get_localized_services(lang)

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        role = request.form.get("role")
        skill_key = request.form.get("skill_key") if role == "provider" else None
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            return "Email already registered! <a href='/login'>Login</a>"

        new_user = User(
            name=name, phone=phone, email=email, role=role, skill_key=skill_key,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        session.permanent = True
        session["user_id"] = new_user.id
        session["user_name"] = new_user.name
        session["user_role"] = new_user.role

        if new_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif new_user.role == "provider":
            return redirect(url_for("dashboard"))
        return redirect(url_for("home"))

    return render_template("signup.html", role=preselected_role, services=services)

@app.route("/login", methods=["GET", "POST"])
def login():
    preselected_role = request.args.get("role", "customer")
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session.permanent = True
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "provider":
                return redirect(url_for("dashboard"))
            return redirect(url_for("home"))
        return "Invalid Credentials! <a href='/login'>Try again</a>"

    return render_template("login.html", role=preselected_role)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("gateway"))

    role = session.get("user_role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))

    current_user_id = int(session.get("user_id"))
    if role == "provider":
        bookings = Booking.query.filter_by(provider_id=current_user_id).order_by(Booking.id.desc()).all()
        provider_reviews = Review.query.filter_by(provider_id=current_user_id).order_by(Review.id.desc()).all()
    else:
        bookings = Booking.query.filter_by(user_id=current_user_id).order_by(Booking.id.desc()).all()
        provider_reviews = []

    return render_template("dashboard.html", bookings=bookings, role=role, name=session.get("user_name"), reviews=provider_reviews)

@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session.get("user_role") != "admin":
        return redirect(url_for("login"))

    all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    all_customers = User.query.filter_by(role="customer").all()
    all_providers = User.query.filter_by(role="provider").all()
    all_reviews = Review.query.order_by(Review.id.desc()).all()

    pending_count = Booking.query.filter_by(status="Pending").count()
    accepted_count = Booking.query.filter_by(status="Accepted").count()
    completed_count = Booking.query.filter_by(status="Completed").count()

    return render_template(
        "admin_dashboard.html",
        bookings=all_bookings,
        customers=all_customers,
        providers=all_providers,
        reviews=all_reviews,
        total_bookings=len(all_bookings),
        pending_count=pending_count,
        accepted_count=accepted_count,
        completed_count=completed_count,
        total_customers=len(all_customers),
        total_providers=len(all_providers)
    )

@app.route("/booking/accept/<int:booking_id>")
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "Accepted"
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/booking/reject/<int:booking_id>")
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "Rejected"
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/booking/complete/<int:booking_id>")
def complete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "Completed"
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/booking/delete/<int:booking_id>")
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/admin/booking/delete/<int:booking_id>")
def admin_delete_booking(booking_id):
    if "user_id" not in session or session.get("user_role") != "admin":
        return redirect(url_for("login"))
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("gateway"))

def open_browser():
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

# ----------------- APP INITIALIZATION (LOCAL + RENDER READY) -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Agar local PC par run ho raha hai toh auto-browser open trigger karein
    if port == 5000 and not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()
    app.run(host="0.0.0.0", port=port, debug=False if os.environ.get("PORT") else True)