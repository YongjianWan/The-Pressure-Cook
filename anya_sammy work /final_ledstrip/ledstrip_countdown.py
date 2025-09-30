import serial
import os
import time

# Adjust to your Arduino port
ser = serial.Serial('/dev/cu.usbmodem3101', 9600)
time.sleep(2)  # allow Arduino to initialize

while True:
    line = ser.readline().decode(errors='ignore').strip()

    if line == "ALARM_WARNING":
        print("Switching tasks soon!")
        os.system('say "Switching tasks soon"')

        # 5-second countdown before LEDs turn on
        for i in range(5, 0, -1):
            print(i)
            os.system(f'say "{i}"')
            time.sleep(0.2)  # shorter delay so countdown fits 5s

    elif line == "ALARM_ON":
        print("Switch tasks now!")
        os.system('say "Switch tasks now"')
