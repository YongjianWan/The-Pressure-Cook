import serial
import os

# adjust port to match your Arduino (check Arduino IDE > Tools > Port)
ser = serial.Serial('/dev/cu.usbmodem3101', 9600)

while True:
    line = ser.readline().decode(errors='ignore').strip()
    if line == "ALARM":
        print("Timer triggered!")
        os.system('say "Alarm triggered"')  # macOS speech
