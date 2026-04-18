import time
import json
import logging
import datetime
import csv
import librtd
from pathlib import Path

# ------------------------------------------------------
# File paths
# ------------------------------------------------------
data_file = Path(
    "/home/meganmason/Documents/projects/cold-content/"
    "snowtemps_raspi/mobile-array/logger_files/instrument_data.txt"
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
# Offsets
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
SAMPLE_INTERVAL = 30    # seconds
SAMPLES_PER_PERIOD = 10 #10 × 30 sec = 5 min
CHANNELS = range(1, 9)

# ------------------------------------------------------
# Wait for first even 5-min boundary before starting
# ------------------------------------------------------
now = datetime.datetime.now()
next_boundary = now.replace(second=0, microsecond=0)
next_boundary -= datetime.timedelta(minutes=now.minute % 5)
next_boundary += datetime.timedelta(minutes=5)

wait_seconds = (next_boundary - datetime.datetime.now()).total_seconds()
logging.info(f"Waiting {wait_seconds:.0f}s until {next_boundary:%H:%M} to begin sampling")
time.sleep(wait_seconds)

# ======================================================
# MAIN LOOP
# ======================================================
while True:

    # Timestamp for this 5-min window
    timestamp = datetime.datetime.now().replace(second=0, microsecond=0)

    # --------------------------------------------------
    # Collect 10 samples, 30 seconds apart
    # --------------------------------------------------
    data_accum = {ch: [] for ch in CHANNELS}

    for i in range(SAMPLES_PER_PERIOD):
        if i > 0:  # skip sleep on first sample
            time.sleep(SAMPLE_INTERVAL)
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
                timestamp,
                ch,
                round(avg_temp, 1),
                round(avg_resi, 0),
                round(avg_corr, 1),
            ])

    logging.info(f"Wrote 5-min averaged data at {timestamp:%Y-%m-%d %H:%M:%S}")

    # --------------------------------------------------
    # Re-anchor to next 5-min boundary from wall clock
    # --------------------------------------------------
    now = datetime.datetime.now()
    next_boundary = now.replace(second=0, microsecond=0)
    next_boundary -= datetime.timedelta(minutes=now.minute % 5)
    next_boundary += datetime.timedelta(minutes=5)

    sleep_time = (next_boundary - datetime.datetime.now()).total_seconds()
    if sleep_time > 0:
        time.sleep(sleep_time)