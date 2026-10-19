# Quick test for CSSL fixed temperature array
# Author: Megan Mason (megan.mason@berkeley.edu)
# Version: 0.2 (10/19/2026)

'''
Reads every RTD sensor once and prints a table to the screen.
Nothing is written to the data or log files.

Usage:
    python3 rtd_run.py          # one reading of all 26 sensors
    python3 rtd_run.py 5        # 5 readings, 30 sec apart (Ctrl+C to stop early)

SENSOR_MAP must match the one in log_rtd.py.
'''

import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path
import librtd

offsets_file = Path(__file__).resolve().parent / 'sensor_offsets.json'

SAMPLE_INTERVAL = 30        # seconds between repeats

# (stack, channel, height_cm, cable_length_cm) — stack is librtd's 0-based hat address
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


# Offsets are optional here, so the test still runs without the json file
try:
    with offsets_file.open() as f:
        offsets_dict = json.load(f)
except FileNotFoundError:
    print(f"No {offsets_file.name} found; corrected temps use offset 0\n")
    offsets_dict = {}


def read_all():
    print(f"Time (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}")

    current_hat = None
    for stack, ch, height, length in SENSOR_MAP:
        # New header block for each hat
        if stack != current_hat:
            current_hat = stack
            print(f"\nHat_{stack + 1}:")
            print(f"{'Ch.':<5}{'Height_cm':>9}{'Cable_cm':>10}{'Sensor':>8}"
                  f"{'Resi':>10}{'Raw_Temp':>10}{'Corr_Temp':>11}  Note")
            print("-" * 72)

        key = f"h{stack}c{ch}"
        json_height, sensor_num, offset = offsets_dict.get(key, [height, '-', 0])

        note = ''
        if key not in offsets_dict and offsets_dict:
            note = 'no offset'
        elif json_height != height:
            note = f'offsets file says {json_height} cm'

        try:
            resi = librtd.getRes(stack, ch)
            temp = librtd.get(stack, ch)
            vals = f"{resi:>10.1f}{temp:>10.2f}{temp + offset:>11.2f}"
        except Exception as e:
            vals = f"{'--':>10}{'--':>10}{'--':>11}"
            note = f"READ ERROR: {e}"

        print(f"{ch:<5}{height:>9}{length:>10}{sensor_num!s:>8}{vals}  {note}")
    print()


if __name__ == '__main__':
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        for i in range(repeats):
            if i > 0:
                time.sleep(SAMPLE_INTERVAL)
            read_all()
    except KeyboardInterrupt:
        print("Stopped.")
