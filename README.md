# 🏙️ Civic Issue Reporting System

A web-based platform that allows citizens to **report civic issues** (like potholes, garbage, streetlight problems, etc.) in their city — helping local authorities take timely action.

---

## 🚀 Features

- 🧍 **User Authentication** — Signup, Login & Logout functionality using MongoDB.
- 📍 **Location Validation** — Ensures reports are submitted only from **Nagpur city** using Reverse Geocoding (OpenStreetMap API).
- 🖼️ **Image Uploads** — Users must upload at least 3 images per issue.
- 🤖 **AI-Powered Issue Detection** — Uses **Hugging Face (DETR model)** to auto-detect issue type from uploaded images.
- 📊 **Dashboard Summary** — Displays total, pending, and solved issues.
- 🌐 **MongoDB Atlas Integration** — Stores all user and issue data securely in the cloud.

---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| Backend | Flask (Python) |
| Database | MongoDB Atlas |
| AI Model | Hugging Face `facebook/detr-resnet-50` |
| Frontend | HTML, CSS, Jinja2 Templates |
| Hosting Ready | GitHub / Render / Railway |

---

## ⚙️ Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/anshumansahu12/civic_issue_reporting.git
cd civic_issue_reporting
python3 -m venv .venv

source .venv/bin/activate   # for Linux/Mac
.venv\Scripts\activate      # for Windows

pip install -r requirements.txt

MONGO_URI="mongodb+srv://<your_mongo_user>:<your_mongo_password>@<cluster_name>.mongodb.net/?retryWrites=true&w=majority"
HF_TOKEN="hf_your_huggingface_token_here"
SECRET_KEY="your_secret_key_here"

python app.py
civic_issue_reporting/
│
├── app.py
├── requirements.txt
├── .env
├── static/
│   └── uploads/
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   └── report.html
└── README.md

