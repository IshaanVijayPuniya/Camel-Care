"""
Camel Care - simple Flask app connecting camel farmers, milk producers, consumers,
researchers, vets, transporters, entrepreneurs and government stakeholders.

Single-file demo app using SQLite + SQLAlchemy + Flask-Login.
This is intentionally compact so you can run it locally and extend it.

To run:
1. create a virtualenv, pip install -r requirements.txt
2. FLASK_APP=app.py FLASK_ENV=development flask run
   or: python app.py
3. Visit http://127.0.0.1:5000

Note: This is a demo. For production, you must:
- Use proper secrets and HTTPS
- Use migrations (Flask-Migrate) and a production DB
- Add input validation, rate-limiting, and secure file handling
"""

import os
from datetime import datetime
from enum import Enum

from flask import (
    Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, current_user, login_user, login_required, logout_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FloatField
from wtforms.validators import InputRequired, Length, Email
from passlib.hash import bcrypt

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "camelcare.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CAMELCARE_SECRET", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# --- Models ---
class RoleEnum(str, Enum):
    FARMER = "farmer"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    RESEARCHER = "researcher"
    VET = "vet"
    TRANSPORTER = "transporter"
    ENTREPRENEUR = "entrepreneur"
    GOV = "gov"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=RoleEnum.FARMER.value)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship("Profile", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)

    def get_role(self):
        return RoleEnum(self.role)


class Profile(db.Model):
    __tablename__ = "profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    full_name = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    location = db.Column(db.String(200))
    bio = db.Column(db.Text)


class Listing(db.Model):
    """
    Generic listing used for milk/product offers, transport offers, vet services, etc.
    """
    __tablename__ = "listings"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    category = db.Column(db.String(80))  # e.g., 'milk', 'transport', 'vet', 'research-collab'
    price = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.String(80), nullable=True)  # e.g., "50 liters/week"
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", backref="listings")


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    subject = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_messages")


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organizer = db.relationship("User", backref="organized_events")


# --- Forms ---
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(3, 80)])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired(), Length(6, 128)])
    role = SelectField("Role", choices=[(r.value, r.value.title()) for r in RoleEnum])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])


class ListingForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired(), Length(2, 200)])
    description = TextAreaField("Description", validators=[InputRequired(), Length(10, 2000)])
    category = SelectField("Category", choices=[
        ("milk", "Milk/Product"), ("transport", "Transport"), ("vet", "Vet Service"),
        ("research", "Research/Collab"), ("other", "Other")
    ])
    price = FloatField("Price (optional)")
    quantity = StringField("Quantity (optional)")
    location = StringField("Location (optional)")


class MessageForm(FlaskForm):
    receiver = StringField("To (username)", validators=[InputRequired()])
    subject = StringField("Subject", validators=[InputRequired(), Length(1, 200)])
    body = TextAreaField("Message", validators=[InputRequired(), Length(1, 2000)])


class EventForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired(), Length(2, 200)])
    description = TextAreaField("Description", validators=[InputRequired(), Length(10, 2000)])
    date = StringField("Date (YYYY-MM-DD)", validators=[InputRequired()])


# --- Login loader ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Routes ---
@app.route("/")
def index():
    # show recent listings and events and quick filters
    q = request.args.get("q", "")
    cat = request.args.get("cat", "")
    listings = Listing.query
    if q:
        listings = listings.filter(Listing.title.contains(q) | Listing.description.contains(q))
    if cat:
        listings = listings.filter_by(category=cat)
    listings = listings.order_by(Listing.created_at.desc()).limit(30).all()
    events = Event.query.order_by(Event.date.asc()).limit(10).all()
    return render_template("index.html", listings=listings, events=events, query=q, cat=cat)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash("Username or email already exists", "danger")
            return redirect(url_for("register"))
        u = User(username=form.username.data, email=form.email.data, role=form.role.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        # create empty profile
        prof = Profile(user_id=u.id, full_name="", phone="", location="", bio="")
        db.session.add(prof)
        db.session.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(username=form.username.data).first()
        if u and u.check_password(form.password.data):
            login_user(u)
            flash("Logged in.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    # show user's listings, messages, events relevant to role
    my_listings = Listing.query.filter_by(owner_id=current_user.id).all()
    inbox = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).limit(20).all()
    organized = Event.query.filter_by(organizer_id=current_user.id).all()
    return render_template("dashboard.html", my_listings=my_listings, inbox=inbox, organized=organized)


@app.route("/listing/new", methods=["GET", "POST"])
@login_required
def new_listing():
    form = ListingForm()
    if form.validate_on_submit():
        l = Listing(
            title=form.title.data,
            description=form.description.data,
            owner_id=current_user.id,
            category=form.category.data,
            price=form.price.data or None,
            quantity=form.quantity.data,
            location=form.location.data
        )
        db.session.add(l)
        db.session.commit()
        flash("Listing created.", "success")
        return redirect(url_for("dashboard"))
    return render_template("new_listing.html", form=form)


@app.route("/listing/<int:listing_id>")
def view_listing(listing_id):
    l = Listing.query.get_or_404(listing_id)
    return render_template("listing.html", l=l)


@app.route("/user/<username>")
def view_user(username):
    u = User.query.filter_by(username=username).first_or_404()
    return render_template("user.html", u=u)


@app.route("/message/new", methods=["GET", "POST"])
@login_required
def new_message():
    form = MessageForm()
    if form.validate_on_submit():
        receiver = User.query.filter_by(username=form.receiver.data).first()
        if not receiver:
            flash("Receiver not found.", "danger")
            return redirect(url_for("new_message"))
        msg = Message(
            sender_id=current_user.id,
            receiver_id=receiver.id,
            subject=form.subject.data,
            body=form.body.data
        )
        db.session.add(msg)
        db.session.commit()
        flash("Message sent.", "success")
        return redirect(url_for("dashboard"))
    return render_template("new_message.html", form=form)


@app.route("/event/new", methods=["GET", "POST"])
@login_required
def new_event():
    form = EventForm()
    if form.validate_on_submit():
        try:
            dt = datetime.strptime(form.date.data, "%Y-%m-%d")
        except Exception:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for("new_event"))
        ev = Event(
            title=form.title.data,
            description=form.description.data,
            date=dt,
            organizer_id=current_user.id
        )
        db.session.add(ev)
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("dashboard"))
    return render_template("new_event.html", form=form)


# --- Simple API endpoints (JSON) for external integrations (mobile app, aggregator) ---
@app.route("/api/listings")
def api_listings():
    """Return simple JSON list of listings with filters q and category."""
    q = request.args.get("q", "")
    cat = request.args.get("category", "")
    qry = Listing.query
    if q:
        qry = qry.filter(Listing.title.contains(q) | Listing.description.contains(q))
    if cat:
        qry = qry.filter_by(category=cat)
    results = []
    for l in qry.order_by(Listing.created_at.desc()).limit(200).all():
        results.append({
            "id": l.id, "title": l.title, "description": l.description,
            "category": l.category, "price": l.price, "quantity": l.quantity,
            "location": l.location, "owner": {"id": l.owner.id, "username": l.owner.username}
        })
    return jsonify(results)


@app.route("/api/users/<int:user_id>")
def api_user(user_id):
    u = User.query.get_or_404(user_id)
    return jsonify({
        "id": u.id, "username": u.username, "email": u.email, "role": u.role,
        "profile": {
            "full_name": u.profile.full_name if u.profile else "",
            "phone": u.profile.phone if u.profile else "",
            "location": u.profile.location if u.profile else "",
            "bio": u.profile.bio if u.profile else ""
        }
    })


# --- Small utilities & seed loader ---
@app.cli.command("initdb")
def initdb_command():
    """Initialize database and add seed data."""
    db.drop_all()
    db.create_all()
    seed_data()
    print("Initialized the database and added seed data.")


def seed_data():
    # Create sample users for each role
    sample_users = [
        ("farmer1", "farmer1@example.com", "farmerpass", RoleEnum.FARMER.value),
        ("producer1", "producer1@example.com", "producerpass", RoleEnum.PRODUCER.value),
        ("consumer1", "consumer1@example.com", "consumerpass", RoleEnum.CONSUMER.value),
        ("research1", "research1@example.com", "researchpass", RoleEnum.RESEARCHER.value),
        ("vet1", "vet1@example.com", "vetpass", RoleEnum.VET.value),
        ("trans1", "trans1@example.com", "transpass", RoleEnum.TRANSPORTER.value),
        ("ent1", "ent1@example.com", "entpass", RoleEnum.ENTREPRENEUR.value),
        ("gov1", "gov1@example.com", "govpass", RoleEnum.GOV.value),
    ]
    users = []
    for u, e, p, r in sample_users:
        user = User(username=u, email=e, role=r)
        user.set_password(p)
        db.session.add(user)
        users.append(user)
    db.session.commit()

    # profiles
    for u in users:
        prof = Profile(user_id=u.id, full_name=u.username.title(), phone="N/A", location="Rajasthan", bio=f"Role: {u.role}")
        db.session.add(prof)
    db.session.commit()

    # sample listings
    l1 = Listing(title="Raw camel milk - weekly supply (50 L)", description="High-quality raw camel milk from free-range camels. Good for research and consumers.", owner_id=users[0].id, category="milk", price=1.5, quantity="50 L/week", location="Bikaner, Rajasthan")
    l2 = Listing(title="Pasteurized camel milk - 10L packs", description="Hygienically pasteurized and packaged. Certified for sale.", owner_id=users[1].id, category="milk", price=2.0, quantity="10 L packs", location="Jaisalmer")
    l3 = Listing(title="Transport service for milk (cold chain)", description="Refrigerated transport available across districts.", owner_id=users[5].id, category="transport", price=0.5, quantity="per km", location="Rajasthan statewide")
    l4 = Listing(title="Veterinary health check & vaccination", description="Experienced camel vet offering herd health checkups.", owner_id=users[4].id, category="vet", price=20.0, quantity="per visit", location="Rajasthan")
    db.session.add_all([l1, l2, l3, l4])
    db.session.commit()

    # events
    ev = Event(title="Camel Conservation Workshop", description="Field workshop on camel nutrition and conservation.", date=datetime.utcnow(), organizer_id=users[7].id)
    db.session.add(ev)
    db.session.commit()

    # messages
    msg = Message(sender_id=users[2].id, receiver_id=users[0].id, subject="Interested in weekly milk", body="Hi, I'd like to buy 20L/week. Can we discuss?")
    db.session.add(msg)
    db.session.commit()


# --- Simple static templates (create templates/ folder with these files) ---
# For demo purposes, templates are expected to exist. We'll ensure helpful error messages if missing.

@app.errorhandler(500)
def handle_500(e):
    return f"Server error: {e}", 500


# --- Run ---
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        db.create_all()
        seed_data()
        print("Database created and seeded.")
    app.run(debug=True)
