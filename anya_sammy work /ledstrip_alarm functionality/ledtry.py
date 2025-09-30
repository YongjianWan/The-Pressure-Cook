import serial
import os
import time

# Adjust port to match your Arduino
ser = serial.Serial('/dev/cu.usbmodem3101', 9600)
time.sleep(2)  # wait for Arduino to start

while True:
    line = ser.readline().decode(errors='ignore').strip()
    if line == "ALARM_ON":
        print("Switch tasks!")
        os.system('say "Switch Tasks"')  # macOS voice alert
        time.sleep(0.5)  # prevent overlapping calls
