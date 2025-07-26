import threading
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
from datetime import datetime
# from train import wait_until_target_time
# from tensorflow.keras.models import load_model
import joblib
import pandas as pd
import numpy as np
import razorpay
from flask import send_from_directory


app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app) 
app.secret_key = 'supersecretkey'

# model = load_model("final_aqi_model.keras")
# scaler = joblib.load("scaler.save")

RAZORPAY_KEY_ID = 'rzp_test_Xgqvn30xIowSSX'
RAZORPAY_KEY_SECRET = 'rIbqHRINIO8P1WIOwZr9Lldl'

# Initialize Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route('/pay')
def show_payment_page():
    return render_template('payment.html', key_id=RAZORPAY_KEY_ID)


@app.route('/payment', methods=['POST'])
def payment():
    # Create Razorpay order
    payment_data = {
        "amount": 500,  # 
        "currency": "INR",
        "payment_capture": 1
    }
    order = client.order.create(data=payment_data)
    return {
        "order_id": order['id']
    }

@app.route("/app")
def serve_react():
    return send_from_directory("frontend", "index.html")

@app.route("/app/<path:path>")
def serve_react_static(path):
    return send_from_directory("frontend", path)


# Set the training time (24-hour format)
TARGET_HOUR = 19
TARGET_MINUTE = 4 # this comment is made using live share 

# Load blockchain
chain = load_chain()

DATA_FILE = 'data.json' # this file will store user data
LATEST_FILE = 'latest_readings.json' # This file will store the latest readings from the sensors
TOKEN_FILE = 'token_ledger.json'



# Ensure the data.json file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Ensure the latest_readings.json file exists
if not os.path.exists(LATEST_FILE):
    with open(LATEST_FILE, 'w') as f:
        json.dump([], f)     

# Ensure the token ledger exists
if not os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({}, f)

# In-memory OTP store   
otp_store = {}


# --- Helper: Load user data from users.json ---
def load_users():
    if not os.path.exists("data.json"):
        return []
    with open("data.json", "r") as f:
        return json.load(f)

def get_token_balance(email):
    with open(TOKEN_FILE, 'r') as f:
        ledger = json.load(f)
    if email not in ledger:
        return 0
    return sum(ledger[email].values())

# def predict_environment(location):
#     df = pd.read_csv("dataset.csv")

#     # Filter by location
#     location_data = df[df["Location"] == location].sort_values("Timestamp")

#     if len(location_data) < 7:
#         return None  # Not enough data

#     # Drop unneeded columns and keep the last 7 rows
#     input_data = location_data.drop(["Timestamp", "Location"], axis=1).tail(7)
#     scaled_input = scaler.transform(input_data)
#     X_input = np.array([scaled_input])

#     # Predict next timestep
#     prediction = model.predict(X_input)[0]

#     # Inverse scale
#     full_df = df.drop(["Timestamp", "Location"], axis=1)
#     dummy = np.zeros((1, full_df.shape[1]))
#     dummy[0] = prediction
#     predicted_values = scaler.inverse_transform(dummy)[0]

#     columns = full_df.columns.tolist()
#     return dict(zip(columns, predicted_values))

def update_token_balance(email, device_id, change):  
    # ✅ Force device_id to start with "sensor_"
    if not device_id.startswith("sensor_"):
        device_id = "sensor_" + device_id

    with open(TOKEN_FILE, 'r') as f:
        ledger = json.load(f)

    if email not in ledger:
        ledger[email] = {}

    # initialize device entry
    if device_id not in ledger[email]:
        ledger[email][device_id] = 0

    # update the token balance
    ledger[email][device_id] += change

    with open(TOKEN_FILE, 'w') as f:
        json.dump(ledger, f, indent=2)

# @app.route("/predict", methods=["GET", "POST"])
# def predict():
#     if request.method == "POST":
#         location = request.form.get("location")
#         date = request.form.get("date")

#         try:
#             df = pd.read_csv("dataset.csv")
#             df = df[df["Location"] == location]
#             df = df.sort_values("Timestamp")

#             feature_columns = [
#                 "mq135_raw", "soil_moisture", "soil_temperature", "speed",
#                 "light_intensity_lux", "sound_level", "rain_detected", "estimated_ppm",
#                 "temperature", "humidity", "pressure", "altitude", "uv_index"
#             ]

#             missing_cols = [col for col in feature_columns if col not in df.columns]
#             if missing_cols:
#                 return f"Missing columns for prediction: {missing_cols}"

#             df_model = df[feature_columns]
#             scaled = scaler.transform(df_model)

#             SEQ_LEN = 7
#             if len(scaled) < SEQ_LEN:
#                 return "Not enough data for prediction"

#             input_seq = scaled[-SEQ_LEN:]
#             input_seq = np.expand_dims(input_seq, axis=0)

#             predicted = model.predict(input_seq)[0]
#             predicted_original = scaler.inverse_transform([predicted])[0]

#             results = dict(zip(feature_columns, predicted_original))

#             return render_template("result.html", results=results, location=location, date=date)

#         except Exception as e:
#             return f"Error: {str(e)}"

#     return render_template("predict.html")

def get_device_token_map(email):
    with open(TOKEN_FILE, 'r') as f:
        ledger = json.load(f)
    return ledger.get(email, {})

def get_tokens_earned_by_email(email):
    with open(TOKEN_FILE, 'r') as f:
        ledger = json.load(f)
    return sum(ledger.get(email, {}).values())


# Dummy location resolver based on latitude
def get_location_from_lat(lat):
    if 18.5 <= lat <= 18.6:
        return "Pune Campus"
    elif 19.0 <= lat <= 19.1:
        return "Mumbai Station"
    elif 20.0 <= lat <= 20.1:
        return "Nashik Field"
    elif 19.09 <= lat <= 19.1:
        return "Ahmednagar Rural"
    return "Unknown"

# --- Route: View earnings for a device ---
@app.route('/earnings')
def view_earnings():
    if 'email' not in session:
        return redirect('/login')
    
    email = session['email']
    total_tokens = get_tokens_earned_by_email(email)
    token_value_inr = total_tokens * 1

    return render_template("earnings.html", 
                           device_id=email,
                           total_tokens=total_tokens,
                           token_value=token_value_inr)




# --- Helper: Send OTP to email using Gmail SMTP ---
def send_email_otp(receiver_email, otp):
    sender_email = "plentera24@gmail.com"
    sender_password = "ajyhlbaqbdbcctuw"  # Use Gmail App Password

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

from datetime import datetime

@app.route('/earnings-table')
def earnings_table():

    print("\n📦 Blockchain rewards:")
    for block in chain.chain:
        data = block.data
        if isinstance(data, dict) and "reward" in data:
            print(data["reward"])



    if 'email' not in session:
        return redirect('/login')

    email = session['email']

    # Step 1: Load user devices
    with open(DATA_FILE, 'r') as f:
        users = json.load(f)

    user_devices = []
    for user in users:
        if user['email'] == email:
            user_devices = user.get('devices', [])
            break

    # Step 2: Load latest readings
    with open(LATEST_FILE, 'r') as f:
        latest_data = json.load(f)

    sensor_info_map = {}  # {deviceId: {date, location}}
    for entry in latest_data:
        device_id = entry['deviceId']
        if device_id in user_devices:
            lat = entry['location']['lat']
            readable_date = datetime.fromtimestamp(entry['timestamp']).strftime('%Y-%m-%d')
            sensor_info_map[device_id] = {
                "date": readable_date,
                "location": get_location_from_lat(lat)
            }

    # ✅ Step 3: Token count from blockchain
    sensor_token_map = get_device_token_map(email)
    for block in chain.chain:
        data = block.data
        if isinstance(data, dict) and "reward" in data:
            reward = data["reward"]
            full_id = reward["to"]  # e.g., sensor_test
            device_name = full_id.replace("sensor_", "")  # e.g., test
            if device_name in user_devices:
                sensor_token_map[device_name] = sensor_token_map.get(device_name, 0) + reward["amount"]

    # Step 4: Final data rows
    rows = []
    for device_id in user_devices:
        info = sensor_info_map.get(device_id, {})
        tokens = sensor_token_map.get(device_id, 0)
        rows.append({
            "date": info.get("date", "N/A"),
            "location": info.get("location", "Unknown"),
            "name": device_id,
            "tokens": tokens,
            "value": tokens  # ₹1 per token
        })

    print("Earnings Table Rows:", rows)
    return render_template("earnings_table.html", data=rows)

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

@app.route("/view-graphs")
def view_graphs():
    return render_template("graphs_by_location.html")


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
        email = request.form.get('email')
        password = request.form.get('password')

        with open(DATA_FILE, 'r') as f:
            users = json.load(f)

        for user in users:
            if user['email'] == email and user['password'] == password:
                session['username'] = user['name']
                session['email'] = user['email']
                session['role'] = user.get('role', 'user')

                user_devices = user.get('devices', [])
                total_tokens = 0
                sensor_token_map = {}
                sensor_info_map = {}

                # Step 1: Load latest sensor readings
                with open(LATEST_FILE, 'r') as f:
                    latest_data = json.load(f)

                for entry in latest_data:
                    device_id = entry['deviceId']  # e.g., sensor_test
                    device_name = device_id.replace("sensor_", "")  # remove 'sensor_' prefix
                    if device_name in user_devices:
                        date = datetime.fromtimestamp(entry['timestamp']).strftime('%Y-%m-%d')
                        lat = entry['location']['lat']
                        sensor_info_map[device_name] = {
                            "date": date,
                            "location": get_location_from_lat(lat)
                        }

                # Step 2: Read blockchain and count tokens
                sensor_token_map = get_device_token_map(email)
                total_tokens = sum(sensor_token_map.values())


                # Step 3: Prepare rows for earnings table
                rows = []
                for device in user_devices:
                    info = sensor_info_map.get(device, {})
                    tokens = sensor_token_map.get(device, 0)
                    rows.append({
                        "date": info.get("date", "N/A"),
                        "location": info.get("location", "Unknown"),
                        "name": device,
                        "tokens": tokens,
                        "value": tokens  # ₹1 per token
                    })

                print("✅ Total tokens:", total_tokens)
                print("✅ Sensor tokens:", sensor_token_map)

                return render_template("loggedIn.html",
                                       user=user['name'],
                                       email=user['email'],
                                       total_tokens=total_tokens,
                                       token_value=total_tokens * 1,
                                       data=rows)

        return "Invalid email or password", 401

    return render_template("login.html")




# --- Route: Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/withdraw', methods=['GET'])
def show_withdraw_page():
    if 'email' not in session:
        return redirect('/login')
    
    email = session['email']
    current_balance = get_token_balance(email)
    return render_template('withdraw.html', balance=current_balance)



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

    # Add timestamp
    data["timestamp"] = time.time()

    # Find the email associated with this sensor
    device_id = data["deviceId"].replace("sensor_", "")  # e.g., test01

    with open(DATA_FILE, 'r') as f:
        users = json.load(f)

    for user in users:
        if device_id in [d.replace("sensor_", "") for d in user.get("devices", [])]:
            update_token_balance(user["email"], data["deviceId"], 1)
            print(f"✅ 1 token rewarded to {user['email']}")
            break  # Found the user, exit loop

    # Save reward transaction to blockchain
    reward_tx = {
        "from": "SYSTEM",
        "to": data["deviceId"],
        "amount": 1,
        "timestamp": time.time()
    }

    block_data = {
        "sensorData": data,
        "reward": reward_tx
    }

    chain.add_block(block_data)
    save_chain(chain)

    # Update latest readings
    with open(LATEST_FILE, 'r+') as f:
        latest = json.load(f)
        latest = [entry for entry in latest if entry["deviceId"] != data["deviceId"]]
        latest.append(data)
        f.seek(0)
        f.truncate()
        json.dump(latest, f, indent=2)

    return jsonify({
        "message": "Block added with 1 token reward",
        "latestBlock": chain.get_latest_block().to_dict()
    })


@app.route('/buy-sensor', methods=['POST'])
def buy_sensor():
    if 'email' not in session:
        return redirect('/login')

    kit_name = request.form.get('kit_name')
    full_name = request.form.get('full_name')
    address = request.form.get('address')

    if not kit_name:
        return "Kit name is required", 400

    # ✅ Always ensure the name starts with 'sensor_'
    if not kit_name.startswith("sensor_"):
        kit_name = "sensor_" + kit_name

    # ✅ Update user's devices in data.json
    with open(DATA_FILE, 'r') as f:
        users = json.load(f)

    for user in users:
        if user['email'] == session['email']:
            devices = user.get("devices", [])
            if kit_name not in devices:
                devices.append(kit_name)
            user['devices'] = devices
            break

    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

    return render_template("success.html", kit_name=kit_name, name=full_name)

@app.route('/withdraw', methods=['POST'])
def withdraw_tokens():
    if 'email' not in session:
        return redirect('/login')

    email = session['email']
    amount_str = request.form.get('amount')

    if not amount_str or not amount_str.isdigit():
        return "⚠️ Invalid amount entered.", 400

    amount = int(amount_str)
    current_balance = get_token_balance(email)

    if amount <= 0:
        return "⚠️ Enter a positive amount", 400

    if amount > current_balance:
        return "⚠️ Not enough tokens to withdraw", 400

    # 🔁 Deduct from individual devices proportionally
    with open(TOKEN_FILE, 'r') as f:
        ledger = json.load(f)

    user_tokens = ledger.get(email, {})
    remaining = amount

    for device_id in list(user_tokens.keys()):
        if remaining <= 0:
            break
        deduct = min(user_tokens[device_id], remaining)
        user_tokens[device_id] -= deduct
        remaining -= deduct

    # Save updated ledger
    ledger[email] = user_tokens
    with open(TOKEN_FILE, 'w') as f:
        json.dump(ledger, f, indent=2)

    # ➕ Add to blockchain
    withdrawal_tx = {
        "from": email,
        "to": "WITHDRAWAL",
        "amount": amount,
        "timestamp": time.time(),
        "type": "withdrawal"
    }

    block_data = {
        "withdrawal": withdrawal_tx
    }

    chain.add_block(block_data)
    save_chain(chain)

    return render_template('success.html', amount=amount)


# --- Route: Get latest block as JSON ---
@app.route('/latest-readings')
def get_latest_readings():
    with open(LATEST_FILE, 'r') as f:
        latest = json.load(f)
    return jsonify(latest)

@app.route('/latest')
def get_latest():
    latest_block = chain.get_latest_block().to_dict()
    return render_template("latest.html", block=latest_block)


# --- Route: Get full blockchain ---
@app.route('/chain', methods=['GET'])
def get_chain():
    return jsonify(chain.to_dict_list())

# --- Route: View chain in browser ---
@app.route('/view-chain')
def view_chain():
    blocks = chain.to_dict_list()
    return render_template("chain.html" , blocks=blocks)

# --- Route: sign_in in browser ---
@app.route('/sign_up')
def sign_up():
    return render_template("sign_up.html")  


# --- Route: Home in browser ---
@app.route('/about')
def about():
    return render_template("about.html")  

# --- Route: Root redirect to login ---
@app.route('/home')
def home():
    return render_template("home.html")

# --- Route: Map ---
@app.route('/map')
def map():
    return render_template("map.html")

# --- Route: Map ---
@app.route('/buy_kit')
def buy_kit():
    return render_template("buy_kit.html")

@app.route('/place_order')
def place_order():
    email = session.get('email', 'not_logged_in@example.com')
    return render_template("place_order.html",email=email)

@app.route('/')
def index():
    return render_template("home.html")

@app.route('/test')
def test():
    return "✅ Test route is working!"

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

    # Only start thread if it's not a reload
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        print("🧵 Starting training thread")
        threading.Thread(
            target=wait_until_target_time,
            args=(TARGET_HOUR, TARGET_MINUTE),
            daemon=True
        ).start()

    app.run(debug=True, port=5000)



def fix_ledger_prefix():
    with open("token_ledger.json", 'r') as f:
        ledger = json.load(f)

    updated = False

    for email in ledger:
        fixed = {}
        for device_id, value in ledger[email].items():
            if not device_id.startswith("sensor_"):
                fixed["sensor_" + device_id] = value
                updated = True
            else:
                fixed[device_id] = value
        ledger[email] = fixed

    if updated:
        with open("token_ledger.json", 'w') as f:
            json.dump(ledger, f, indent=2)
        print("✅ Prefixes fixed in token_ledger.json")
    else:
        print("✅ No changes needed")

