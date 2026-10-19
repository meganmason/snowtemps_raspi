#!/bin/bash
sleep 60
source /home/meganmason/rpi/bin/activate
cd /home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/RTD_array_jellyfish_wy27/scripts
/home/meganmason/rpi/bin/python log_rtd.py
