# 🐄 Local Setup Guide

## 🚀 Quick Steps to Run Locally

### 1️⃣ Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### 2️⃣ Create Templates and Save `app.py`
Make sure your `app.py` and HTML templates are in place before proceeding.

---

### 3️⃣ Initialize the Database and Seed Data
You can initialize the database using either of the following commands:

```bash
flask --app app.py initdb
# OR
python app.py   # First run auto-creates the DB and seeds data
```

---

### 4️⃣ Run the Application
```bash
python app.py
```

Then open your browser and visit:  
👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔐 Sample Seeded Accounts

Use any of the following credentials to log in:

| Role | Username | Password |
|------|-----------|-----------|
| 🧑‍🌾 Farmer | `farmer1` | `farmerpass` |
| 🧑‍🔬 Producer | `producer1` | `producerpass` |
| 🧑‍💼 Consumer | `consumer1` | `consumerpass` |
| 🧑‍🔬 Researcher | `research1` | `researchpass` |
| 🩺 Veterinarian | `vet1` | `vetpass` |
| 🚚 Transporter | `trans1` | `transpass` |
| 🏢 Enterprise | `ent1` | `entpass` |
| 🏛️ Government | `gov1` | `govpass` |

---

## 💡 Next Recommended Enhancements

Take your platform to the next level with these suggested improvements:

- 📂 **File uploads** for certificates and product photos (Amazon S3 or secure local storage)
- 💳 **Payments / Escrow integration** (Razorpay / Stripe)
- 📊 **Role-based dashboards** with analytics (milk volumes, conservation KPIs)
- 📱 **Mobile-friendly UI** built in React Native or Flutter consuming `/api/*` endpoints
- 🧰 **Moderation tools**, reporting, and verification workflows for producers & vets
- 🗺️ **GIS mapping** for farm locations and cold-chain routes
- 🔔 **Push notifications / SMS** alerts for orders and urgent vet cases
- 🔒 **Enhanced authentication** — JWT for API, two-factor auth, and rate limiting

---

✨ **You’re all set!**  
Run the project locally, log in using the sample accounts, and start building new features 🚀
