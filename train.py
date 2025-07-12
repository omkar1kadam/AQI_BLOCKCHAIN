# === Updated train.py ===

import time
from datetime import datetime
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Conv1D, Dense, Flatten, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
import json
import os

print("✅ train.py was imported")


def extract_data_from_blockchain(chain_file, csv_file):
    if not os.path.exists(chain_file):
        print("❌ Blockchain file not found!")
        return

    with open(chain_file, 'r', encoding='utf-8') as f:
        chain = json.load(f)

    rows = []
    for block in chain:
        for key in ['sensorData', 'sensor_data']:
            if isinstance(block.get('data'), dict) and key in block['data']:
                data = block['data'][key]

                loc = data["location"]
                env = data["environment"]
                soil = data["soil"]

                location_id = f"{loc['lat']:.4f}_{loc['lon']:.4f}"

                row = {
                    "Location": location_id,
                    "Timestamp": data.get("timestamp"),
                    "mq135_raw": env["air_quality"]["mq135_raw"],
                    "soil_moisture": soil["moisture"],
                    "soil_temperature": soil["temperature"],
                    "speed": loc["speed"],
                    "light_intensity_lux": env["light_intensity_lux"],
                    "sound_level": env["sound_level"],
                    "rain_detected": int(env["rain_detected"]),
                    "estimated_ppm": env["air_quality"]["estimated_ppm"],
                    "temperature": env["temperature"],
                    "humidity": env["humidity"],
                    "pressure": env["pressure"],
                    "altitude": env["altitude"],
                    "uv_index": env["uv_index"]
                }

                rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(csv_file, index=False)
    print(f"✅ Extracted {len(df)} rows to {csv_file}")


def train_model():
    print(f"🧠 Training started at {datetime.now()}")

    # Step 0: Prepare dataset from blockchain
    extract_data_from_blockchain("chain.json", "dataset.csv")

    # Step 1: Load dataset
    df = pd.read_csv('dataset.csv')
    df = df.drop(['Timestamp', 'Location'], axis=1)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    # Step 2: Scale the features
    scaler = RobustScaler()
    scaled_data = scaler.fit_transform(df)

    # Step 3: Time-series windowing
    SEQ_LEN = 7
    X, y = [], []
    for i in range(len(scaled_data) - SEQ_LEN):
        X.append(scaled_data[i:i + SEQ_LEN])
        y.append(scaled_data[i + SEQ_LEN])

    X, y = np.array(X), np.array(y)

    # Step 4: Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Step 5: Build CNN model
    inputs = Input(shape=(X_train.shape[1], X_train.shape[2]))
    x = Conv1D(64, kernel_size=2, activation='relu')(inputs)
    x = Conv1D(32, kernel_size=2, activation='relu')(x)
    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.2)(x)
    outputs = Dense(y_train.shape[1], activation='linear')(x)

    model = Model(inputs, outputs)
    model.compile(optimizer=Adam(learning_rate=0.0001), loss='mse')

    # Step 6: Train
    early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    checkpoint = ModelCheckpoint('best_aqi_model.h5', monitor='val_loss', save_best_only=True)

    model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=32,
        validation_split=0.1,
        callbacks=[early_stop, checkpoint],
        verbose=1
    )

    # Step 7: Save model & scaler
    model.save('final_aqi_model.keras')
    joblib.dump(scaler, 'scaler.save')

    print("✅ Model and scaler saved successfully!")


# Daily trainer runner
last_trained_date = None

def wait_until_target_time(hour, minute):
    global last_trained_date
    print(f"⏳ Waiting for daily training at {hour:02d}:{minute:02d}...")

    while True:
        now = datetime.now()
        current_date = now.date()

        if now.hour == hour and now.minute == minute:
            if last_trained_date != current_date:
                extract_data_from_blockchain("data/blockchain.json", "dataset.csv")
                train_model()
                last_trained_date = current_date
            else:
                print(f"⚠️ Already trained today at {hour:02d}:{minute:02d}")
            time.sleep(60)
        else:
            time.sleep(10)


if __name__ == '__main__':
    TARGET_HOUR = 11
    TARGET_MINUTE = 38
    wait_until_target_time(TARGET_HOUR, TARGET_MINUTE)
