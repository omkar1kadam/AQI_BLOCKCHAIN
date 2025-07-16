import json
import matplotlib.pyplot as plt
from datetime import datetime
import base64
import io
from collections import defaultdict
import os

# Create templates directory if not exist
os.makedirs("templates", exist_ok=True)

# Load blockchain data
with open("data/blockchain.json", "r") as f:
    blockchain = json.load(f)

# Group sensor data by (lat, lon)
location_data = defaultdict(list)

for block in blockchain:
    try:
        sensor = block["data"]["sensorData"]
        timestamp = sensor["timestamp"]
        lat = sensor["location"]["lat"]
        lon = sensor["location"]["lon"]
        temp = sensor["environment"]["temperature"]
        hum = sensor["environment"]["humidity"]
        mq135 = sensor["environment"]["air_quality"]["mq135_raw"]

        location_key = f"{lat},{lon}"
        location_data[location_key].append({
            "time": datetime.fromtimestamp(timestamp),
            "temperature": temp,
            "humidity": hum,
            "mq135": mq135
        })
    except KeyError:
        continue  # Skip if data is malformed

# Function to generate base64 graph image
def plot_to_base64(location, readings):
    times = [r["time"] for r in readings]
    temps = [r["temperature"] for r in readings]
    hums = [r["humidity"] for r in readings]
    mq135s = [r["mq135"] for r in readings]

    plt.figure(figsize=(10, 5))
    plt.plot(times, temps, label="Temperature (°C)", color="red", marker='o')
    plt.plot(times, hums, label="Humidity (%)", color="blue", marker='x')
    plt.plot(times, mq135s, label="MQ135 Raw", color="green", marker='s')
    plt.title(f"Sensor Data for Location: {location}")
    plt.xlabel("Timestamp")
    plt.ylabel("Value")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode('utf-8')
    return encoded

# Build HTML
html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sensor Graphs by Location</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h2 { margin-top: 50px; }
        img { border: 1px solid #ccc; margin-top: 10px; }
        hr { margin-top: 40px; }
    </style>
</head>
<body>
    <h1>Sensor Graphs by Location</h1>
"""

for location, readings in location_data.items():
    if len(readings) < 2:
        continue  # Need at least 2 points to plot
    sorted_readings = sorted(readings, key=lambda r: r["time"])
    img_data = plot_to_base64(location, sorted_readings)
    html += f"<h2>Location: {location}</h2>\n"
    html += f'<img src="data:image/png;base64,{img_data}" alt="Graph for {location}"><hr>\n'

html += "</body></html>"

# Write to template file
with open("templates/graphs_by_location.html", "w") as f:
    f.write(html)

print("✅ Template generated: templates/graphs_by_location.html")
