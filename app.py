from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
import os, uuid, time, requests

# ---------------- Load Environment Variables ----------------
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

# ---------------- Flask App ----------------
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------- MongoDB Atlas ----------------
client = MongoClient(MONGO_URI)
db = client["civic_issue_reporting"]
users_collection = db["users"]
issues_collection = db["issues"]

# ---------------- Uploads ----------------
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- Reverse Geocode ----------------
def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "jsonv2", "lat": lat, "lon": lon, "accept-language": "en"}
    headers = {"User-Agent": "CivicIssueReporting/1.0 (anshuman@example.com)"}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ---------------- Home ----------------
@app.route('/')
def index():
    total = issues_collection.count_documents({})
    solved = issues_collection.count_documents({"status": "Solved"})
    pending = issues_collection.count_documents({"status": "Pending"})
    avg_time = "N/A"
    user = session.get("user")
    return render_template('index.html', total=total, solved=solved, pending=pending, avg_time=avg_time, user=user)

# ---------------- Auth ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if users_collection.find_one({"email": email}):
            return "Email already registered!"

        users_collection.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "password": password
        })
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_collection.find_one({"email": email, "password": password})
        if user:
            session['user'] = user['name']
            session['email'] = user['email']
            return redirect(url_for('index'))
        return "Invalid email or password!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)
    return redirect(url_for('index'))

# ---------------- Report ----------------
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        images = request.files.getlist('images')
        if not images or len(images) < 3:
            return "Please upload at least 3 images.", 400

        lat = request.form.get('lat')
        lng = request.form.get('lng')
        address_client = request.form.get('address', '')
        if not lat or not lng:
            return "Location required.", 400

        try:
            geo = reverse_geocode(lat, lng)
        except Exception as e:
            print("Reverse geocode failed:", e)
            return "Server error while validating location.", 500

        address_display = geo.get('display_name', '') or address_client
        addr_obj = geo.get('address', {})
        city_candidates = [addr_obj.get(k, '') for k in ('city', 'town', 'village', 'county', 'state')]
        city_combined = " ".join([c for c in city_candidates if c]).lower()

        if 'nagpur' not in address_display.lower() and 'nagpur' not in city_combined:
            return "Location validation failed: not in Nagpur.", 400

        saved_paths = []
        for f in images:
            if f and f.filename.strip():
                filename = secure_filename(f.filename)
                unique = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{filename}"
                dest = os.path.join(UPLOAD_DIR, unique)
                f.save(dest)
                saved_paths.append(f"/static/uploads/{unique}")

        category = request.form.get('category') or 'Other'
        description = request.form.get('description') or ''

        issues_collection.insert_one({
            "user": session.get('user'),
            "user_email": session.get('email'),
            "category": category,
            "description": description,
            "images": saved_paths,
            "lat": float(lat),
            "lng": float(lng),
            "address": address_display,
            "status": "Pending",
            "created_at": datetime.utcnow()
        })
        return redirect(url_for('index'))

    return render_template('report.html')

# ---------------- AI Describe ----------------
@app.route('/ai/describe', methods=['POST'])
def ai_describe():
    img = request.files.get("image")
    if not img or img.filename.strip() == "":
        return jsonify({"error": "No image uploaded"}), 400

    img_bytes = img.read()
    API_URL = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        files = {"file": (img.filename, img_bytes)}
        hf_resp = requests.post(API_URL, headers=headers, files=files, timeout=60)
        hf_resp.raise_for_status()
    except Exception as e:
        print("HF request error:", e)
        return jsonify({"error": "Failed to call Hugging Face API"}), 500

    try:
        result = hf_resp.json()
    except Exception as e:
        print("Invalid HF JSON:", e)
        return jsonify({"error": "Invalid response from Hugging Face"}), 500

    labels = []
    if isinstance(result, list):
        for item in result:
            labels.append({"label": item.get("label", "Unknown"), "score": item.get("score", 0)})
    else:
        labels.append({"label": str(result), "score": 0})

    top = max(labels, key=lambda x: x["score"], default={"label": "Unknown", "score": 0})
    top_label = top["label"]
    top_score = top["score"]

    mapping = {
        "pothole": "Road / Potholes",
        "hole": "Road / Potholes",
        "road": "Road / Potholes",
        "garbage": "Garbage",
        "trash": "Garbage",
        "rubbish": "Garbage",
        "streetlight": "Streetlight",
        "lamp": "Streetlight",
        "pole": "Streetlight",
        "water": "Water Supply",
        "drain": "Drainage",
        "manhole": "Road / Potholes",
        "car": "Road / Traffic",
        "vehicle": "Road / Traffic",
        "tree": "Other"
    }

    predicted_category = next((v for k, v in mapping.items() if k in top_label.lower()), "Other")
    description = f"Auto-detected: {top_label} (confidence {top_score:.2f})."

    return jsonify({"category": predicted_category, "description": description, "raw_labels": labels})

if __name__ == '__main__':
    app.run(debug=True)
