# Datalogger program for CSSL fixed temperature array
# Author: Megan Mason (megan.mason@berkeley.edu)
# Version: 0.1 (11/10/2025)
# Background info: Bare-nylon RTD vertical array w/ 15 cm spacing
# Resolution: +/-0.1 C 
# Data reporting period(s) - 5 mins

'''
This script logs data for the fixed array of RTD sensors.
This array has 32 sensors, 8 sensors per hat

    Hat_1: 0, 15, 30, 45, 60, 75, 90, 105 cm (channels 1-8)
    Hat_2: 120, 135, 150, 165, 180, 195, 210, 225 cm (channels 1-8)
    Hat_3: 240, 255, 270, 285, 300, 315, 330, 345 cm (channels 1-8)
    Hat_4: 360, 375, 390, 405, 420, 435, 450, 465 cm (channels 1-8)

Data are sampled every 30 seconds, and 5 min avg is recorded (300 sec)

A temperature offset is applyed to the corrected temp field using a .json file to apply the offset
'''


import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import librtd

# ------------------------------------------------------
# File paths
# ------------------------------------------------------
data_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_data.csv')
log_file  = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_log.txt')

# ------------------------------------------------------
# Logging function
# ------------------------------------------------------
def log_message(message):
    """Append message with UTC timestamp to the log file."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with log_file.open('a') as f:
        f.write(f"[{timestamp}] {message}\n")


# ------------------------------------------------------
# Load sensor offsets
# ------------------------------------------------------
with open('sensor_offsets.json') as f:
    offsets_dict = json.load(f)

log_message("Instrument restarted")


# ------------------------------------------------------
# Write header if data file does not yet exist
# ------------------------------------------------------
if not data_file.is_file():
    with data_file.open('w') as f:
        f.write("Time(UTC),Hat,Channel,Height_cm,Sensor_Number,Resistance_ohms,"
                "RawTemp_degC,CorrectedTemp_degC\n")


# ------------------------------------------------------
# Sampling settings
# ------------------------------------------------------
SAMPLE_INTERVAL = 30        # seconds
SAMPLES_PER_PERIOD = 10     # 10 samples × 30 sec = 5 min

# Precompute sensor keys
sensor_keys = [(hat, ch, f"h{hat}c{ch}") for hat in range(4) for ch in range(1, 9)]

# Prepare accumulator for 5-min window
data_accum = {(hat, ch): [] for hat in range(4) for ch in range(1, 9)}


# ------------------------------------------------------
# Align to next even 5-minute boundary
# ------------------------------------------------------
now = datetime.utcnow()
prev_minute = now.minute - (now.minute % 5)
aligned = now.replace(minute=prev_minute, second=0, microsecond=0)
aligned += timedelta(minutes=5)

# log_message(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")


# ======================================================
# MAIN LOOP — 30-sec sampling + 5-min averaging
# ======================================================
while True:

    # --------------------------------------------------
    # Collect 10 samples spaced 30 sec apart
    # --------------------------------------------------
    for _ in range(SAMPLES_PER_PERIOD):
        for hat, ch, key in sensor_keys:
            try:
                resi = librtd.getRes(hat, ch)
                temp = librtd.get(hat, ch)
            except Exception as e:
                resi = float('nan')
                temp = float('nan')
                log_message(f"Error reading {key}: {e}")

            # Offset file format: [height_cm, sensor_number, offset]
            height, sensor_num, offset = offsets_dict.get(
                key, [float('nan'), float('nan'), 0]
            )

            corr_temp = temp + offset

            # Accumulate in 5-min storage
            data_accum[(hat, ch)].append((resi, temp, corr_temp))

        time.sleep(SAMPLE_INTERVAL)


    # --------------------------------------------------
    # Write 5-min averages
    # --------------------------------------------------
    timestamp_5min = aligned

    with data_file.open('a') as f:
        for hat, ch, key in sensor_keys:
            samples = data_accum[(hat, ch)]

            if len(samples) > 0:
                avg_resi = sum(s[0] for s in samples) / len(samples)
                avg_temp = sum(s[1] for s in samples) / len(samples)
                avg_corr = sum(s[2] for s in samples) / len(samples)
            else:
                avg_resi = avg_temp = avg_corr = float('nan')

            height, sensor_num, offset = offsets_dict.get(
                key, [float('nan'), float('nan'), 0]
            )

            line = (
                f"{timestamp_5min:%Y-%m-%d %H:%M:%S},"
                f"{hat},{ch},{height},{sensor_num},"
                f"{avg_resi:.1f},{avg_temp:.2f},{avg_corr:.2f}\n"
            )
            f.write(line)

    log_message(f"Logged 5-min averaged data at {timestamp_5min:%Y-%m-%d %H:%M:%S}")

    # Clear accumulators for next 5-min window
    data_accum = {(hat, ch): [] for hat in range(4) for ch in range(1, 9)}

    # --------------------------------------------------
    # Schedule next 5-min timestamp
    # --------------------------------------------------
    aligned += timedelta(minutes=5)
    # log_message(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")

    # Sleep until the next even 5-min boundary
    now = datetime.utcnow()
    sleep_time = (aligned - now).total_seconds()
    if sleep_time > 0:
        time.sleep(sleep_time)








