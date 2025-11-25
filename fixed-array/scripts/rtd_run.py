# Imports
import librtd
import json
import pandas as pd

# Load offsets from file
with open('sensor_offsets.json') as f:
    offsets_dict = json.load(f) # hat<#>channel<#>: sensor_height, offset_value, e.g h0c5: [345, -0.1]

# Create an empty list to store all readings
data = []

# Loop through RTD hats (0 to 3)
for i in range(4):  
    # Loop through RTD channels (1 to 8)
    for j in range(1, 9): 
        resi = librtd.getRes(i, j)
        temp = librtd.get(i, j)
        
        # Temperature correction
        key = f"h{i}c{j}"
        offset = offsets_dict.get(key)[2]
        corr_temp = temp + offset

        # Append data as a dict 
        data.append({
            "Hat": i,
            "Ch.": j, 
            "Resi": resi,
            "Raw_Temp": temp,
            "Corr_Temp": corr_temp
        })

# Convert to DataFrame
df = pd.DataFrame(data)

# print('DATAFRAME', df)

# Optional: map hat stacks to human-readable names
hat_map = {
    0: "Hat_1",
    1: "Hat_2",
    2: "Hat_3",
    3: "Hat_4"
}
df["Hat_Name"] = df["Hat"].map(hat_map)

# Print formatted output grouped by hat
for hat_name, group in df.groupby("Hat_Name"):
    print(f"\n{hat_name}:")
    print(f"{'Ch.':<6}{'Resi':<12}{'Raw_Temp':<12}{'Corr_Temp':<12}")
    print("-" * 42)
    
    for _, row in group.iterrows():
        print(f"{row['Ch.']:<6}{row['Resi']:<12.0f}{row['Raw_Temp']:<12.1f}{row['Corr_Temp']:<12.1f}")


