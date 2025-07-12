# predict.py
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
import joblib

# Load model and scaler
model = load_model("final_aqi_model.keras")
scaler = joblib.load("scaler.save")

# All the input columns used during training
FEATURE_COLUMNS = [
    "mq135_raw", "soil_moisture", "soil_temperature", "speed",
    "light_intensity_lux", "sound_level", "rain_detected", "estimated_ppm"
]

# All the output columns to predict
OUTPUT_COLUMNS = [
    "temperature", "humidity", "pressure", "altitude", "uv_index"
]

def predict_environment(location, date):
    # For now, generate dummy input values (or retrieve from DB if needed)
    # In real world, fetch latest or average of past sensor data for that location
    dummy_input = {
        "mq135_raw": 210,
        "soil_moisture": 45.0,
        "soil_temperature": 27.0,
        "speed": 1.0,
        "light_intensity_lux": 700,
        "sound_level": 2.0,
        "rain_detected": 0,
        "estimated_ppm": 310,
    }

    input_df = pd.DataFrame([dummy_input])
    scaled_input = scaler.transform(input_df)
    prediction = model.predict(scaled_input)[0]

    result = dict(zip(OUTPUT_COLUMNS, prediction.round(2)))
    result["location"] = location
    result["date"] = date
    return result
