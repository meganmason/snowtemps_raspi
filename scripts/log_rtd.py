import logging
import datetime
import pandas as pd
import time
import csv
import librtd

# Configure logging
LOG_FILE = "/home/meganmason/Documents/projects/cold-content/logger_files/instrument_log.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Define constants
SENSOR_SAMPLING_INTERVAL = 30  # Collect every 30 seconds
ROLLING_WINDOW = "5min"  # 5-minute rolling window using pandas Grouper
OUTPUT_CSV = "/home/meganmason/Documents/projects/cold-content/logger_files/instrument_log.csv"

# Offset values for each channel (update these as needed)
offset_dict = {
    1: 1.2,  # channel 1 offset
    2: 1.3,  # channel 2 offset
    3: 1.3,  # channel 3 offset
    4: 1.2,  # channel 4 offset
    5: 0.9,  # channel 5 offset
    6: 1.2,  # channel 6 offset
    7: 1.3,  # channel 7 offset
    8: 1.3   # channel 8 offset
}

# Data storage for rolling aggregation
sensor_data = pd.DataFrame(columns=["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])

def read_sensors():
    """Reads temperature, resistance, and calculates corrected temperature for all channels."""
    readings = []
    timestamp = datetime.datetime.now()
    
    for channel in range(1, 9):
        temp = librtd.get(0, channel)  # Read temperature (C)
        resi = librtd.getRes(0, channel)  # Read resistance (ohms)
        corr_temp = temp - offset_dict[channel]  # Apply correction

        readings.append([timestamp, channel, round(temp, 4), round(resi, 2), round(corr_temp, 4)])

    return readings

def log_data():
    """Collects data every 30 seconds and logs rolling 5-minute averages to CSV."""
    global sensor_data
    
    # Read sensor data and append to DataFrame
    new_data = pd.DataFrame(read_sensors(), columns=["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])
    sensor_data = pd.concat([sensor_data, new_data]).tail(600)  # Keep only the last 10 minutes
    
    # Ensure timestamp is in datetime format
    sensor_data["Timestamp"] = pd.to_datetime(sensor_data["Timestamp"])

def log_rolling_averages():
    """Calculates and logs rolling averages for every 5-minute window."""
    global sensor_data

    # Compute rolling averages every 5 minutes using Grouper
    rolling_avg = (
        sensor_data.groupby(["Channel", pd.Grouper(key="Timestamp", freq=ROLLING_WINDOW)])
        .agg({"Temp": "mean", "Resi": "mean", "Corr_Temp": "mean"})
        .reset_index()
    )

    # Save rolling averages to CSV
    with open(OUTPUT_CSV, mode="a", newline="") as file:
        writer = csv.writer(file)
        if file.tell() == 0:  # Write header if file is new
            writer.writerow(["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])
        
        for _, row in rolling_avg.iterrows():
            writer.writerow([row["Timestamp"], row["Channel"], round(row["Temp"], 1), round(row["Resi"], 0), round(row["Corr_Temp"], 1)])

    # Log event
    log_msg = f"Logged rolling averages: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_msg)

def main():
    """Main loop to collect data every 30 seconds and log 5-minute averages."""
    logging.info("Starting instrument logger.")
    last_logged_time = datetime.datetime.now()

    try:
        while True:
            current_time = datetime.datetime.now()
            
            # Collect data every 30 seconds
            log_data()
            
            # Check if it's time to log the rolling average (5-minute interval)
            if (current_time - last_logged_time).seconds >= 300:  # 5 minutes
                last_logged_time = current_time
                log_rolling_averages()  # Only log rolling averages once every 5 minutes
                
            # Sleep until the next data collection
            time.sleep(SENSOR_SAMPLING_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Logging stopped by user.")
        # print("\nLogging stopped.")

# Run the main function
if __name__ == "__main__":
    main()


# import logging
# import datetime
# import pandas as pd
# import time
# import csv
# import librtd 

# # Configure logging
# LOG_FILE = "/home/meganmason/Documents/projects/cold-content/logger_files/instrument_log.txt"
# logging.basicConfig(
#     filename=LOG_FILE,
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
# )

# # Define constants
# SENSOR_SAMPLING_INTERVAL = 30 # Collect every 30 seconds
# ROLLING_WINDOW = "5min"  # 5-minute rolling window using pandas Grouper
# OUTPUT_CSV = "/home/meganmason/Documents/projects/cold-content/logger_files/instrument_log.csv"

# # Offset values for each channel (update these as needed)
# offset_dict = {
#     1: 1.2,  # channel 1 offset
#     2: 1.3,  # channel 2 offset
#     3: 1.3,  # channel 3 offset
#     4: 1.2,  # channel 4 offset
#     5: 0.9,  # channel 5 offset
#     6: 1.2,  # channel 6 offset
#     7: 1.3,  # channel 7 offset
#     8: 1.3   # channel 8 offset
# }

# # Data storage for rolling aggregation
# sensor_data = pd.DataFrame(columns=["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])

# def read_sensors():
#     """Reads temperature, resistance, and calculates corrected temperature for all channels."""
#     readings = []
#     timestamp = datetime.datetime.now()
    
#     for channel in range(1, 9):
#         temp = librtd.get(0, channel)  # Read temperature (C)
#         resi = librtd.getRes(0, channel)  # Read resistance (ohms)
#         corr_temp = temp - offset_dict[channel]  # Apply correction

#         readings.append([timestamp, channel, round(temp, 4), round(resi, 2), round(corr_temp, 4)])

#     return readings

# def log_data():
#     """Collects data every 30 seconds and logs rolling 5-minute averages to CSV."""
#     global sensor_data
    
#     # Read sensor data and append to DataFrame
#     new_data = pd.DataFrame(read_sensors(), columns=["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])
#     sensor_data = pd.concat([sensor_data, new_data]).tail(600)
       
#     # Ensure timestamp is in datetime format
#     sensor_data["Timestamp"] = pd.to_datetime(sensor_data["Timestamp"])
    
#     # Compute rolling averages every 5 minutes using Grouper
#     rolling_avg = (
#         sensor_data.groupby(["Channel", pd.Grouper(key="Timestamp", freq=ROLLING_WINDOW)])
#         .agg({"Temp": "mean", "Resi": "mean", "Corr_Temp": "mean"})
#         .reset_index()
#     )


#     # Save rolling averages to CSV
#     with open(OUTPUT_CSV, mode="a", newline="") as file:
#         writer = csv.writer(file)
#         if file.tell() == 0:  # Write header if file is new
#             writer.writerow(["Timestamp", "Channel", "Temp", "Resi", "Corr_Temp"])
        
#         for _, row in rolling_avg.iterrows():
#             writer.writerow([row["Timestamp"], row["Channel"], round(row["Temp"], 1), round(row["Resi"], 0), round(row["Corr_Temp"], 1)])

#     # Log event
#     log_msg = f"Logged rolling averages: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
#     logging.info(log_msg)

#     # print(f"Logged rolling averages at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# def main():
#     """Main loop to collect data every 30 seconds and log 5-minute averages."""
#     logging.info("Starting instrument logger.")
#     last_logged_time = datetime.datetime.now()
#     # print("Logging rolling averages... (Ctrl+C to stop)")
    
#     try:
#         while True:
#             current_time = datetime.datetime.now()
            
#             # Collect data every 30 seconds
#             log_data()
            
#             # Check if it's time to log the rolling average (5-minute interval)
#             if (current_time - last_logged_time).seconds >= 300:  # 5 minutes
#                 last_logged_time = current_time
#                 print("5 minutes passed, logging rolling average.")
                
#             # Sleep until the next data collection
#             time.sleep(SENSOR_SAMPLING_INTERVAL)
#     except KeyboardInterrupt:
#         logging.info("Logging stopped by user.")
#         print("\nLogging stopped.")

# # Run the main function
# if __name__ == "__main__":
#     main()

# #     try:
# #         while True:
# #             log_data()
# #             time.sleep(SENSOR_SAMPLING_INTERVAL)
# #     except KeyboardInterrupt:
# #         logging.info("Logging stopped by user.")
# #         # print("\nLogging stopped.")

# # if __name__ == "__main__":
# #     main()
