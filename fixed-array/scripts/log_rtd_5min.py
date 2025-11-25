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

Data is collected every 5 mins (300 sec)

A temperature offset is applyed to the corrected temp field using a .json file to apply the offset
'''


import datetime
import time
from datetime import datetime, timedelta
from pathlib import Path
import librtd
import json
import os

# Set period
period = 300 # 5min=300sec

# Load offsets from file
with open('sensor_offsets.json') as f:
    offsets_dict = json.load(f)

# Set up logger files (1: data, 2:log txt file)
data_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_data.csv')
log_file = Path('/home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/logger_files/rtd_tower_log.txt')

def log_message(message):
    """Append message with UTC timestamp to log file"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with log_file.open('a') as log:
        log.write(f"[{timestamp}] {message}\n")

# Write a restart message
log_message("Instrument restarted")

# Add header to CSV data file
if not data_file.is_file():
    with data_file.open('w') as f:
        f.write("Time (UTC),Hat_no,Channel,Height_cm,Resistance_ohms,Raw_Temp_degC,Corrected_Temp_degC\n")

# Start logging loop
time_rounded = datetime.utcnow()
prev_minute = time_rounded.minute - (time_rounded.minute % 5)
time_rounded = time_rounded.replace(minute=prev_minute, second=0, microsecond=0)

while True:
    # Wait until the next 5-minute interval
    time_rounded += timedelta(minutes=5)
    time_to_wait = (time_rounded - datetime.utcnow()).total_seconds()
    if time_to_wait < 0:
        time_to_wait = 0
    time.sleep(time_to_wait)

    timestamp_tz = datetime.utcnow()

    with data_file.open('a') as f:
        # Loop through RTD hats (0-3) and channels (1-8)
        for hat in range(4):
            for ch in range(1, 9):
                try:
                    resi = librtd.getRes(hat, ch)
                    temp = librtd.get(hat, ch)
                except Exception as e:
                    resi = float('nan')
                    temp = float('nan')
                    log_message(f"Error reading sensor h{hat}c{ch}: {e}")

                # Look up offset, height, & sensor num.
                key = f"h{hat}c{ch}"
                height, sensor, offset = offsets_dict.get(key, [float('nan'), 0])
                corr_temp = temp + offset

                # Write data line to CSV
                line = f"{timestamp_tz:%Y-%m-%d %H:%M:%S},{hat},{ch},{sensor},{height},{resi:.0f},{temp:.1f},{corr_temp:.1f}\n"
                f.write(line)

    # Log successful data write
    log_message(f"Logged RTD sensor array at {timestamp_tz:%Y-%m-%d %H:%M:%S}")


