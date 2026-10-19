# Datalogger program for CSSL fixed temperature array
# Author: Megan Mason (megan.mason@berkeley.edu)
# Version: 0.2 (10/19/2026)
# Background info: Bare-nylon RTD vertical array w/ 15 cm spacing, sensors hang from above
# Resolution: +/-0.1 C
# Data reporting period(s) - 5 mins

'''
This script logs data for the fixed array of RTD sensors.
This array has 26 sensors hanging from a top support. Each sensor has:
    height       - true height above ground (cm); negative = below ground
    cable length - length of cable from the top support (cm)

Hat numbers below are 1-based (as labeled on the stack); librtd uses
0-based stack levels, so Hat 1 = stack 0, ..., Hat 4 = stack 3.

    Hat_1: heights 360, 345, 330, 315, 300, 285, 270, 255 cm (channels 1-8)
    Hat_2: heights 240, 225, 210, 195, 180, 165, 150, 135 cm (channels 1-8)
    Hat_3: heights 120, 105,  90,  75,  60,  45,  30,  15 cm (channels 1-8)
    Hat_4: heights   0,  -5 cm                              (channels 1-2)

The -5 cm sensor is buried; it uses the 375 cm cable but sits at -5 cm,
so its effective drop is 365 cm.

Data are sampled every 30 seconds, and the 5 min avg is recorded (300 sec).
Each record is timestamped (UTC) with the START of its 5-min window,
i.e. the 12:00:00 record averages samples taken 12:00:00 - 12:04:30.
Samples are scheduled on fixed clock times, so timestamps do not drift.

A temperature offset (sensor_offsets.json, in the same folder as this script)
is added to the raw temp to give the corrected temp.

Outputs:
    rtd_tower_data.txt - comma-delimited, one row per sensor per 5-min record:
        Time(UTC)          - start of the 5-min window (YYYY-MM-DD HH:MM:SS)
        Hat                - hat number, 1-4
        Channel            - channel on that hat, 1-8
        Height_cm          - sensor height above ground (negative = below ground)
        CableLength_cm     - cable length from the top support
        Sensor_Number      - physical sensor ID (from sensor_offsets.json)
        N_Samples          - number of good 30-sec samples in the average (max 10)
        Resistance_ohms    - mean resistance
        RawTemp_degC       - mean temperature, no offset
        CorrectedTemp_degC - mean temperature with offset applied
    rtd_tower_log.txt  - restarts, read errors, offset warnings, timing notes (UTC)

Changes from v0.1 (2025 season, 32 sensors on a fixed tower):
    - 26 hanging sensors (360 cm to -5 cm); Hat 1 / Ch 1 is now the top sensor
    - Heights from SENSOR_MAP below, not from the offsets file
    - Output is .txt; added CableLength_cm and N_Samples; Hat is now 1-4 (was 0-3)
    - Fixed 5-min timestamp drift (read time used to add up across windows)
'''


import os
import math
import time
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import librtd

# ------------------------------------------------------
# File paths
# ------------------------------------------------------
data_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/RTD_array_jellyfish_wy27/logger_files/rtd_tower_data.txt')
log_file  = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/RTD_array_jellyfish_wy27/logger_files/rtd_tower_log.txt')

# Offsets live next to this script, so it works no matter which directory it is launched from
offsets_file = Path(__file__).resolve().parent / 'sensor_offsets.json'

# ------------------------------------------------------
# Sampling settings
# ------------------------------------------------------
SAMPLE_INTERVAL = 30        # seconds
SAMPLES_PER_PERIOD = 10     # 10 samples × 30 sec = 5 min
PERIOD = timedelta(seconds=SAMPLE_INTERVAL * SAMPLES_PER_PERIOD)

# ------------------------------------------------------
# Sensor map: (stack, channel, height_cm, cable_length_cm)
#   stack is librtd's 0-based hat address (Hat 1 = stack 0)
# ------------------------------------------------------
SENSOR_MAP = [
    # Hat 1
    (0, 1, 360,   0),
    (0, 2, 345,  15),
    (0, 3, 330,  30),
    (0, 4, 315,  45),
    (0, 5, 300,  60),
    (0, 6, 285,  75),
    (0, 7, 270,  90),
    (0, 8, 255, 105),
    # Hat 2
    (1, 1, 240, 120),
    (1, 2, 225, 135),
    (1, 3, 210, 150),
    (1, 4, 195, 165),
    (1, 5, 180, 180),
    (1, 6, 165, 195),
    (1, 7, 150, 210),
    (1, 8, 135, 225),
    # Hat 3
    (2, 1, 120, 240),
    (2, 2, 105, 255),
    (2, 3,  90, 270),
    (2, 4,  75, 285),
    (2, 5,  60, 300),
    (2, 6,  45, 315),
    (2, 7,  30, 330),
    (2, 8,  15, 345),
    # Hat 4
    (3, 1,   0, 360),
    (3, 2,  -5, 375),   # buried; 375 cm cable placed at -5 cm (365 cm effective drop)
]


# ------------------------------------------------------
# Time helpers (all UTC)
# ------------------------------------------------------
def utc_now():
    return datetime.now(timezone.utc)


def next_boundary(t):
    """Return the next even 5-minute boundary strictly after t."""
    floored = t.replace(minute=t.minute - (t.minute % 5), second=0, microsecond=0)
    return floored + PERIOD


def sleep_until(target):
    """Sleep until the wall-clock time `target` (no-op if already past)."""
    delay = (target - utc_now()).total_seconds()
    if delay > 0:
        time.sleep(delay)


def mean_finite(values):
    """Mean of the non-NaN values, plus how many were used."""
    good = [v for v in values if not math.isnan(v)]
    if not good:
        return float('nan'), 0
    return sum(good) / len(good), len(good)


# ------------------------------------------------------
# Logging function
# ------------------------------------------------------
def log_message(message):
    """Append message with UTC timestamp to the log file."""
    timestamp = utc_now().strftime('%Y-%m-%d %H:%M:%S')
    with log_file.open('a') as f:
        f.write(f"[{timestamp}] {message}\n")


log_message("Instrument restarted")


# ------------------------------------------------------
# Load sensor offsets
#   format: {"h{stack}c{ch}": [height_cm, sensor_number, offset_degC], ...}
#   Height comes from SENSOR_MAP; the json height is only checked for consistency.
# ------------------------------------------------------
with offsets_file.open() as f:
    offsets_dict = json.load(f)

sensors = []
for stack, ch, height, length in SENSOR_MAP:
    key = f"h{stack}c{ch}"
    if key in offsets_dict:
        json_height, sensor_num, offset = offsets_dict[key]
        if json_height != height:
            log_message(f"WARNING: {key} offsets file height {json_height} != SENSOR_MAP height {height}")
    else:
        sensor_num, offset = float('nan'), 0.0
        log_message(f"WARNING: no offset for {key} (height {height} cm); using 0")
    sensors.append((stack, ch, key, height, length, sensor_num, offset))


# ------------------------------------------------------
# Write header if data file does not yet exist
# ------------------------------------------------------
if not data_file.is_file():
    with data_file.open('w') as f:
        f.write("Time(UTC),Hat,Channel,Height_cm,CableLength_cm,Sensor_Number,N_Samples,"
                "Resistance_ohms,RawTemp_degC,CorrectedTemp_degC\n")


# ======================================================
# MAIN LOOP — 30-sec sampling + 5-min averaging
#
# Every sample is scheduled against an absolute clock time
# (window_start + i * 30 s) rather than "read, then sleep 30 s".
# The old approach added the sensor read time to every sample,
# so each 5-min window ran long and the true sample times slowly
# drifted away from the timestamps written to the CSV.
# ======================================================
window_start = next_boundary(utc_now())
log_message(f"First 5-min window starts {window_start:%Y-%m-%d %H:%M:%S}")

while True:

    sleep_until(window_start)

    # If we are well past the window start (e.g. clock was stepped forward
    # by NTP, or the Pi stalled), skip to the next boundary instead of
    # firing a burst of back-to-back samples.
    lag = (utc_now() - window_start).total_seconds()
    if lag > SAMPLE_INTERVAL:
        new_start = next_boundary(utc_now())
        log_message(f"Running {lag:.0f} s behind; realigning window "
                    f"{window_start:%H:%M:%S} -> {new_start:%H:%M:%S}")
        window_start = new_start
        continue

    data_accum = {key: [] for _, _, key, *_ in sensors}

    # --------------------------------------------------
    # Collect 10 samples at window_start + 0, 30, ..., 270 s
    # --------------------------------------------------
    for i in range(SAMPLES_PER_PERIOD):
        sleep_until(window_start + timedelta(seconds=i * SAMPLE_INTERVAL))

        for stack, ch, key, height, length, sensor_num, offset in sensors:
            try:
                resi = librtd.getRes(stack, ch)
                temp = librtd.get(stack, ch)
            except Exception as e:
                resi = float('nan')
                temp = float('nan')
                log_message(f"Error reading {key} (height {height} cm): {e}")

            data_accum[key].append((resi, temp, temp + offset))

    # --------------------------------------------------
    # Write 5-min averages (NaN samples are skipped; N_Samples = valid count)
    # --------------------------------------------------
    with data_file.open('a') as f:
        for stack, ch, key, height, length, sensor_num, offset in sensors:
            samples = data_accum[key]
            avg_resi, n_good = mean_finite([s[0] for s in samples])
            avg_temp, _ = mean_finite([s[1] for s in samples])
            avg_corr, _ = mean_finite([s[2] for s in samples])

            f.write(
                f"{window_start:%Y-%m-%d %H:%M:%S},"
                f"{stack + 1},{ch},{height},{length},{sensor_num},{n_good},"
                f"{avg_resi:.1f},{avg_temp:.2f},{avg_corr:.2f}\n"
            )
        # Push to the SD card now so a power cut loses at most one record
        f.flush()
        os.fsync(f.fileno())

    log_message(f"Wrote 5-min averaged data for {window_start:%Y-%m-%d %H:%M:%S}")

    window_start += PERIOD
