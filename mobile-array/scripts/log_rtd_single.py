import time
import json
import logging
import datetime
import pandas as pd
import csv
import librtd
from pathlib import Path

'''
Note - this is name '_single' but still has some serial 
fetching components. It also doesn't sort into OPIE I,II,III 
directories any more, so if you start here and want that feature
you'll need updates or everything will overwrite
'''

# ------------------------------------------------------
# File paths
# ------------------------------------------------------
data_file = Path(
    "/home/meganmason/Documents/projects/cold-content/"
    "snowtemps_raspi/mobile-array/logger_files/instrument_log.csv"
)
log_file = Path(
    "/home/meganmason/Documents/projects/cold-content/"
    "snowtemps_raspi/mobile-array/logger_files/instrument_log.txt"
)

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.info("Instrument restarted")

# ------------------------------------------------------
# Offsets (Script A style)
# ------------------------------------------------------
with open("sensor_offsets.json") as f:
    offsets_all = json.load(f)

def get_pi_serial():
    with open("/proc/cpuinfo") as f:
        for line in f:
            if line.startswith("Serial"):
                return line.strip().split(":")[1].strip()
    return "00000000"

pi_serial = get_pi_serial()
offset_dict = offsets_all.get(pi_serial, {})

# ------------------------------------------------------
# Write header once
# ------------------------------------------------------
if not data_file.exists():
    with data_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])

# ------------------------------------------------------
# Sampling settings
# ------------------------------------------------------
SAMPLE_INTERVAL = 30        # seconds
SAMPLES_PER_PERIOD = 10     # 10 × 30 sec = 5 min
CHANNELS = range(1, 9)

# ------------------------------------------------------
# Align to next even 5-minute boundary (LOCAL TIME)
# ------------------------------------------------------
now = datetime.datetime.now()
prev_minute = now.minute - (now.minute % 5)
aligned = now.replace(minute=prev_minute, second=0, microsecond=0)
aligned += datetime.timedelta(minutes=5)

# logging.info(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")

# ======================================================
# MAIN LOOP — deterministic 5-min bins
# ======================================================
while True:

    # --------------------------------------------------
    # Fresh accumulator for this 5-min window
    # --------------------------------------------------
    data_accum = {ch: [] for ch in CHANNELS}

    # --------------------------------------------------
    # Collect 10 samples (30 sec apart)
    # --------------------------------------------------
    for _ in range(SAMPLES_PER_PERIOD):
        for ch in CHANNELS:
            try:
                temp = librtd.get(0, ch)
                resi = librtd.getRes(0, ch)
            except Exception as e:
                temp = float("nan")
                resi = float("nan")
                logging.error(f"Error reading channel {ch}: {e}")

            corr_temp = temp - offset_dict.get(f"ch_{ch}", 0)
            data_accum[ch].append((temp, resi, corr_temp))

        time.sleep(SAMPLE_INTERVAL)

    # --------------------------------------------------
    # Write 5-min averages
    # --------------------------------------------------
    with data_file.open("a", newline="") as f:
        writer = csv.writer(f)

        for ch in CHANNELS:
            samples = data_accum[ch]

            if samples:
                avg_temp = sum(s[0] for s in samples) / len(samples)
                avg_resi = sum(s[1] for s in samples) / len(samples)
                avg_corr = sum(s[2] for s in samples) / len(samples)
            else:
                avg_temp = avg_resi = avg_corr = float("nan")

            writer.writerow([
                aligned,
                ch,
                round(avg_temp, 1),
                round(avg_resi, 0),
                round(avg_corr, 1),
            ])

    logging.info(f"Wrote 5-min averaged data at {aligned:%Y-%m-%d %H:%M:%S}")

    # --------------------------------------------------
    # Schedule next 5-min boundary
    # --------------------------------------------------
    aligned += datetime.timedelta(minutes=5)
    # logging.info(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")

    # Sleep until the next boundary
    now = datetime.datetime.now()
    sleep_time = (aligned - now).total_seconds()
    if sleep_time > 0:
        time.sleep(sleep_time)