#!/bin/bash
sleep 60
source /home/meganmason/rpi/bin/activate
cd /home/meganmason/Documents/projects/cold-content/snowtemps_raspi/fixed-array/scripts
/home/meganmason/rpi/bin/python log_rtd.py
