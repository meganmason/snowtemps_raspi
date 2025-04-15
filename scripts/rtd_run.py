import librtd

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


# channel 1
t_ch1 = librtd.get(0, 1)
r_ch1 = librtd.getRes(0, 1)
c_ch1 = t_ch1-offset_dict.get(1)

# channel 2
t_ch2 = librtd.get(0, 2)
r_ch2 = librtd.getRes(0, 2)
c_ch2 = t_ch2-offset_dict.get(2)

# channel 3
t_ch3 = librtd.get(0, 3)
r_ch3 = librtd.getRes(0, 3)
c_ch3 = t_ch3-offset_dict.get(3)

# channel 4
t_ch4 = librtd.get(0, 4)
r_ch4 = librtd.getRes(0, 4)
c_ch4 = t_ch4-offset_dict.get(4)

# channel 5
t_ch5 = librtd.get(0, 5)
r_ch5 = librtd.getRes(0, 5)
c_ch5 = t_ch5-offset_dict.get(5)

# channel 6
t_ch6 = librtd.get(0, 6)
r_ch6 = librtd.getRes(0, 6)
c_ch6 = t_ch6-offset_dict.get(6)

# channel 7
t_ch7 = librtd.get(0, 7)
r_ch7 = librtd.getRes(0, 7)
c_ch7 = t_ch7-offset_dict.get(7)

# channel 8
t_ch8 = librtd.get(0, 8)
r_ch8 = librtd.getRes(0, 8)
c_ch8 = t_ch8-offset_dict.get(8)


# Print table header
print(f"{'Ch. #':<6}{'Temp (C)':<12}{'Resistance (ohms)':<12}{'Corr_Temp (C)':<12}")

# Print each channel's data
for i, (t, r, c) in enumerate([
    (t_ch1, r_ch1, c_ch1), (t_ch2, r_ch2, c_ch2), (t_ch3, r_ch3, c_ch3), (t_ch4, r_ch4, c_ch4),
    (t_ch5, r_ch5, c_ch5), (t_ch6, r_ch6, c_ch6), (t_ch7, r_ch7, c_ch7), (t_ch8, r_ch8, c_ch8)
], start=1):
    print(f"{i:<6}{t:<12.1f}{r:<12.0f}{c:<12.1f}")
    