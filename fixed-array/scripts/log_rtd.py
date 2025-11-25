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

log_message(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")


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

    log_message(f"Wrote 5-min averaged data at {timestamp_5min:%Y-%m-%d %H:%M:%S}")

    # Clear accumulators for next 5-min window
    data_accum = {(hat, ch): [] for hat in range(4) for ch in range(1, 9)}

    # --------------------------------------------------
    # Schedule next 5-min timestamp
    # --------------------------------------------------
    aligned += timedelta(minutes=5)
    log_message(f"Next 5-min average scheduled for {aligned:%Y-%m-%d %H:%M:%S}")

    # Sleep until the next even 5-min boundary
    now = datetime.utcnow()
    sleep_time = (aligned - now).total_seconds()
    if sleep_time > 0:
        time.sleep(sleep_time)





# # Set period
# period = 300 # 5min=300sec

# # Load offsets from file
# with open('sensor_offsets.json') as f:
#     offsets_dict = json.load(f)

# # Set up logger files (1: data, 2:log txt file)
# data_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_data.csv')
# log_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_log.txt')

# def log_message(message):
#     """Append message with UTC timestamp to log file"""
#     timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
#     with log_file.open('a') as log:
#         log.write(f"[{timestamp}] {message}\n")

# # Write a restart message
# log_message("Instrument restarted")

# # Add header to CSV data file
# if not data_file.is_file():
#     with data_file.open('w') as f:
#         f.write("Time (UTC),Hat_no,Channel,Height_cm,Resistance_ohms,Raw_Temp_degC,Corrected_Temp_degC\n")

# # Align to the next even 5-minute boundary
# now = datetime.utcnow()
# prev_minute = now.minute - (now.minute % 5)
# aligned = now.replace(minute=prev_minute, second=0, microsecond=0)

# # Move forward to the NEXT 5-minute boundary
# aligned += timedelta(minutes=5)

# log_message(f"Next 5-min avg scheduled for {aligned:%Y-%m-%d %H:%M:%S}")

# # Start logging with 30-second sampling + 5-min averages
# SAMPLE_INTERVAL = 30         # seconds
# SAMPLES_PER_PERIOD = 10      # 5 minutes / 30 sec = 10 samples

# # Precompute sensor keys
# # sensor_keys = [(hat, ch, f"h{hat}c{ch}") for hat in range(4) for ch in range(1, 9)]

# # Prepare 5-minute bin storage:
# # data_accum[(hat, ch)] = list of tuples (resi, temp, corr_temp)
# data_accum = {(hat, ch): [] for hat in range(4) for ch in range(1, 9)}

# while True:

#     # Collect 10 samples (each 30 sec apart)
#     for _ in range(SAMPLES_PER_PERIOD):

#         for hat, ch, key in sensor_keys:
#             try:
#                 resi = librtd.getRes(hat, ch)
#                 temp = librtd.get(hat, ch)
#             except Exception as e:
#                 resi = float('nan')
#                 temp = float('nan')
#                 log_message(f"Read error on {key}: {e}")

#             # offsets_dict returns: [height_cm, sensor_number, offset_value]
#             height, sensor, offset = offsets_dict.get(
#                 key, [float('nan'), float('nan'), 0]
#             )
#             corr_temp = temp + offset

#             # Accumulate sample
#             data_accum[(hat, ch)].append((resi, temp, corr_temp))

#         # Sleep until next 30-second mark
#         time.sleep(SAMPLE_INTERVAL)

 
#     # After 10 samples → compute averages + write row
#     timestamp_5min = aligned

#     with data_file.open('a') as f:
#         for hat, ch, key in sensor_keys:
#             samples = data_accum[(hat, ch)]

#             if len(samples) == 0:
#                 avg_resi = float('nan')
#                 avg_temp = float('nan')
#                 avg_corr = float('nan')
#             else:
#                 # average across recorded samples
#                 avg_resi = sum(s[0] for s in samples) / len(samples)
#                 avg_temp = sum(s[1] for s in samples) / len(samples)
#                 avg_corr = sum(s[2] for s in samples) / len(samples)

#             height, sensor, offset = offsets_dict.get(
#                 key, [float('nan'), float('nan'), 0]
#             )

#             # Write averaged record
#             line = (
#                 f"{timestamp_5min:%Y-%m-%d %H:%M:%S},{hat},{ch},"
#                 f"{height},{sensor},{avg_resi:.1f},{avg_temp:.2f},{avg_corr:.2f}\n"
#             )
#             f.write(line)

#         # Clear accumulators for next 5-min period
#         data_accum = {(hat, ch): [] for hat in range(4) for ch in range(1, 9)}

#     log_message(f"5-min averaged record written at {timestamp_5min:%Y-%m-%d %H:%M:%S}")


# # Start logging loop
# time_rounded = datetime.utcnow()
# prev_minute = time_rounded.minute - (time_rounded.minute % 5)
# time_rounded = time_rounded.replace(minute=prev_minute, second=0, microsecond=0)

# while True:
#     # Wait until the next 5-minute interval
#     time_rounded += timedelta(minutes=5)
#     time_to_wait = (time_rounded - datetime.utcnow()).total_seconds()
#     if time_to_wait < 0:
#         time_to_wait = 0
#     time.sleep(time_to_wait)

#     timestamp_tz = datetime.utcnow()

#     with data_file.open('a') as f:
#         # Loop through RTD hats (0-3) and channels (1-8)
#         for hat in range(4):
#             for ch in range(1, 9):
#                 try:
#                     resi = librtd.getRes(hat, ch)
#                     temp = librtd.get(hat, ch)
#                 except Exception as e:
#                     resi = float('nan')
#                     temp = float('nan')
#                     log_message(f"Error reading sensor h{hat}c{ch}: {e}")

#                 # Look up offset, height, & sensor num.
#                 key = f"h{hat}c{ch}"
#                 height, sensor, offset = offsets_dict.get(key, [float('nan'), 0])
#                 corr_temp = temp + offset

#                 # Write data line to CSV
#                 line = f"{timestamp_tz:%Y-%m-%d %H:%M:%S},{hat},{ch},{sensor},{height},{resi:.0f},{temp:.1f},{corr_temp:.1f}\n"
#                 f.write(line)

#     # Log successful data write
#     log_message(f"Logged RTD sensor array at {timestamp_tz:%Y-%m-%d %H:%M:%S}")


