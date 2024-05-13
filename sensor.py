from datetime import datetime
import json
import serial
import requests

ser = serial.Serial("/dev/cu.usbserial-210", 9600)

url = "https://2384c1b28266.ngrok.app/record"

while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode("utf-8").strip()
        is_triggered = line == "MOTION_DETECT"
        payload = json.dumps({"is_triggered": is_triggered})
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic NjYzZjU0ZTg3MDNkMjU3NmJhMWZkYWI5OjEyMzQ1Njc4",
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        print(datetime.now(), "is_triggered:", is_triggered, "response status:", response.status_code)
