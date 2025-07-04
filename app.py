import time
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from blockchain.chain import Blockchain
from blockchain.storage import save_chain, load_chain
import os
import json
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_cors import CORS

app = Flask(__name__, template_folder="templates")
CORS(app) 
app.secret_key = 'supersecretkey'

# Load blockchain
chain = load_chain()

DATA_FILE = 'data.json' # this file will store user data
LATEST_FILE = 'latest_readings.json' # This file will store the latest readings from the sensors


# Ensure the data.json file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Ensure the latest_readings.json file exists
if not os.path.exists(LATEST_FILE):
    with open(LATEST_FILE, 'w') as f:
        json.dump([], f)


# In-memory OTP store   
otp_store = {}

# --- Helper: Load user data from users.json ---
def load_users():
    if not os.path.exists("data.json"):
        return []
    with open("data.json", "r") as f:
        return json.load(f)

# --- Helper: Send OTP to email using Gmail SMTP ---
def send_email_otp(receiver_email, otp):
    sender_email = "plentera24@gmail.com"
    sender_password = "yftmsrxpucsamnwd"  # Use Gmail App Password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Your OTP for Plentera Login"

    body = f"Your OTP is: {otp}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# --- Route: Send OTP ---
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp

    if send_email_otp(email, otp):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Failed to send OTP"}), 500

# --- Route: Verify OTP ---
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get("email")
    otp_input = data.get("otp")

    correct_otp = otp_store.get(email)
    if correct_otp and otp_input == correct_otp:
        otp_store.pop(email)
        return jsonify({"verified": True})
    else:
        return jsonify({"verified": False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # from form input `name="username"`
        password = request.form.get('password')

        # Load users from data.json
        with open("data.json", "r") as f:
            users = json.load(f)

        # Check for matching user
        for user in users:
            if user['email'] == email and user['password'] == password:
                session['username'] = user['name']
                return render_template("loggedIn.html", user=user['name'])  # ✅ success!

        return "Invalid email or password", 401

    return render_template("login.html")


# --- Route: Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- Route: Dashboard (protected) ---
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    latest = chain.get_latest_block().to_dict()
    return render_template("index.html", block=latest, user=session['username'], role=session['role'])

# --- Route: Receive Sensor Data (ESP32 POSTs here) ---
@app.route('/aqi', methods=['POST'])
def receive_sensor_data():
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    # Save to blockchain
    chain.add_block(data)
    save_chain(chain)

    # --- ✅ Update latest_readings.json ---
    with open(LATEST_FILE, 'r+') as f:
        latest = json.load(f)

        # Remove previous entry for the same sensor (if exists)
        latest = [entry for entry in latest if entry["deviceId"] != data["deviceId"]]

        # Add current reading with timestamp
        data["timestamp"] = time.time()
        latest.append(data)

        # Overwrite file with updated list
        f.seek(0)
        f.truncate()
        json.dump(latest, f, indent=2)

    return jsonify({
        "message": "Block added",
        "latestBlock": chain.get_latest_block().to_dict()
    })


# --- Route: Get latest block as JSON ---
@app.route('/latest-readings')
def get_latest_readings():
    with open(LATEST_FILE, 'r') as f:
        latest = json.load(f)
    return jsonify(latest)



# --- Route: Get full blockchain ---
@app.route('/chain', methods=['GET'])
def get_chain():
    return jsonify(chain.to_dict_list())

# --- Route: View chain in browser ---
@app.route('/view-chain')
def view_chain():
    if 'username' not in session:
        return redirect('/login')

    blocks = chain.to_dict_list()
    return render_template("chain.html" , blocks=blocks)

# --- Route: sign_in in browser ---
@app.route('/sign_up')
def sign_up():
    return render_template("sign_up.html")  

# --- Route: Home in browser ---
@app.route('/home')
def home1():
    return render_template("home.html")   

# --- Route: Home in browser ---
@app.route('/about')
def about():
    return render_template("about.html")  

# --- Route: Root redirect to login ---
@app.route('/')
def home():
    return redirect('/home')

# --- Route: Map ---
@app.route('/map')
def map():
    return render_template("map.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print("FORM SUBMITTED ✅")
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if fields are present
        if not name or not email or not password:
            return "All fields are required", 400

        new_user = {
            "name": name,
            "email": email,
            "password": password
        }

        print("Name:", name)
        print("Email:", email)
        print("Password:", password)

        # Load existing users from data.json
        with open(DATA_FILE, 'r') as f:
            users = json.load(f)

        # Check for duplicate email
        for user in users:
            if user["email"] == email:
                return "Email already registered!", 400

        users.append(new_user)

        # Save the updated list
        with open(DATA_FILE, 'w') as f:
            json.dump(users, f, indent=4)

        return redirect('/login')  # You can change this to a thank-you page too

    return render_template('sign_up.html')


# --- Start Flask App ---
if __name__ == '__main__':
    os.makedirs("data", exist_ok=True)
    app.run(debug=True, port=5000)
