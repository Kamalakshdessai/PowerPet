from flask import Flask, request, jsonify
import RPi.GPIO as GPIO
import time
import threading
from datetime import datetime

app = Flask(__name__)

latest_data = {
    "battery_status": "OK",
    "feed_left": "200",
    "water_left": "400",
    "feed_ack": "Completed"
}

feeding_schedule = []
triggered_times = set()

# Pin configuration
IN1 = 26
IN2 = 19
IN3 = 13
IN4 = 6

# GPIO setup
def initialize_pins():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(1, GPIO.OUT)
    GPIO.setup(25, GPIO.OUT)
    GPIO.setup(7, GPIO.OUT)
    GPIO.setup(8, GPIO.OUT)
    GPIO.setup(IN1, GPIO.OUT)
    GPIO.setup(IN2, GPIO.OUT)
    GPIO.setup(IN3, GPIO.OUT)
    GPIO.setup(IN4, GPIO.OUT)
    GPIO.output(1, GPIO.LOW)
    GPIO.output(25, GPIO.LOW)
    GPIO.output(7, GPIO.LOW)
    GPIO.output(8, GPIO.LOW)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

# Motor control functions
def stop_motor():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

def rotate_clockwise(duration):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    time.sleep(duration)
    stop_motor()

def rotate_counter_clockwise(duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    time.sleep(duration)
    stop_motor()

def feed_food(f_value):
    if f_value < 100:
        print("Feed weight too low, skipping feed operation.")
        return
    max_time = 1.75  # Max duration for 300 grams
    duration = (f_value / 300) * max_time  # Proportional duration
    print(f"Feeding food for F={f_value} grams with duration {duration:.2f} seconds.")
    rotate_counter_clockwise(duration)
    time.sleep(2)  # Wait for food to drop
    rotate_clockwise(duration)

# Control GPIO pins for water and flushing
def givewater():
    GPIO.output(1, GPIO.HIGH)
    GPIO.output(25, GPIO.LOW)
    time.sleep(5)
    GPIO.output(1, GPIO.LOW)
    GPIO.output(25, GPIO.LOW)

def flushwater():
    GPIO.output(7, GPIO.HIGH)
    GPIO.output(8, GPIO.LOW)
    time.sleep(5)
    GPIO.output(7, GPIO.LOW)
    GPIO.output(8, GPIO.LOW)

def monitor_schedule():
    global latest_data, triggered_times
    while True:
        now = datetime.now()
        current_time = (now.hour, now.minute)
        GPIO.output(1, GPIO.LOW)
        GPIO.output(25, GPIO.LOW)
        GPIO.output(7, GPIO.LOW)
        GPIO.output(8, GPIO.LOW)
        for schedule in feeding_schedule:
            hour, minute, f_value = schedule
            if (hour, minute) == current_time and (hour, minute) not in triggered_times:
                print(f"Feeding Time Triggered: {hour}:{minute} with F={f_value}")
                feed_food(f_value)
                givewater()
                time.sleep(5)
                flushwater()
                water_left = int(latest_data.get("water_left", 0)) - 50
                latest_data["water_left"] = str(max(water_left, 0))
                print("Updated Data:", latest_data)
                triggered_times.add((hour, minute))
        if now.second == 59:
            triggered_times.clear()
        time.sleep(1)

@app.route('/get_message', methods=['GET', 'POST'])
def get_message():
    global latest_data, feeding_schedule
    if request.method == 'GET':
        print("GET Request Received")
        print("Sending Data:", latest_data)
        return jsonify(latest_data), 200
    if request.method == 'POST':
        try:
            data = request.data.decode('utf-8')
            print("POST Request Received")
            print("Raw Data Received:", repr(data))
            feeding_schedule = []
            for match in data.split(","):
                match = match.strip()
                if match.startswith("[H:") and match.endswith("]"):
                    hour = int(match.split(";")[0].split(":")[1])
                    minute = int(match.split(";")[1].split(":")[1])
                    f_value = int(match.split(";")[2].split(":")[1].rstrip("]"))
                    feeding_schedule.append([hour, minute, f_value])
            print("Updated Feeding Schedule:", feeding_schedule)
            return {"message": "Data received successfully"}, 200
        except Exception as e:
            print("Error processing POST request:", e)
            return {"error": str(e)}, 400

if __name__ == '__main__':
    try:
        initialize_pins()
        threading.Thread(target=monitor_schedule, daemon=True).start()
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
 
