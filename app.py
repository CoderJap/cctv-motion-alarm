from flask import Flask, jsonify, Response
import cv2
import time
import threading
import smtplib
from email.mime.text import MIMEText
from playsound import playsound
import atexit
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Variables for motion detection
motion_detected = False
camera = cv2.VideoCapture(0)  # You can change to the index of your camera or use a video file
previous_frame = None

# Alarm Function
def play_alarm_sound():
    playsound("alert.wav")  # Make sure alert.wav is in your working directory

# Function to send an alert email
def send_email_alert():
    sender_email = os.getenv("EMAIL_USER")  # Get email from .env file
    receiver_email = os.getenv("RECIPIENT_EMAIL")  # Get recipient email from .env file
    subject = "Motion Detected: CCTV Alert"
    body = "Motion detected by your CCTV system. Please check your surroundings."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, os.getenv("EMAIL_PASSWORD"))  # Use the app password from .env file
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Alert email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# Function to detect motion
def detect_motion():
    global motion_detected, previous_frame, camera
    while True:
        _, frame = camera.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if previous_frame is None:
            previous_frame = gray
            continue

        # Calculate the difference
        delta_frame = cv2.absdiff(previous_frame, gray)
        thresh = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        (contours, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Check if motion is detected
        motion_detected = any(cv2.contourArea(c) > 1000 for c in contours)

        # Actions on motion detected
        if motion_detected:
            threading.Thread(target=play_alarm_sound).start()
            threading.Thread(target=send_email_alert).start()
            time.sleep(5)  # Pause to avoid duplicate alerts

        previous_frame = gray
        time.sleep(0.1)

# Route to start motion detection
@app.route('/start_detection', methods=['GET'])
def start_detection():
    global detection_thread
    detection_thread = threading.Thread(target=detect_motion)
    detection_thread.daemon = True
    detection_thread.start()
    return jsonify({"status": "Motion detection started"})

# Route to stop motion detection
@app.route('/stop_detection', methods=['GET'])
def stop_detection():
    global camera
    camera.release()
    return jsonify({"status": "Motion detection stopped"})

# Route to stream the video
@app.route('/video_feed')
def video_feed():
    def generate():
        global camera
        while True:
            success, frame = camera.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Register the cleanup function to release the camera when the app shuts down
def cleanup():
    global camera
    if camera.isOpened():
        camera.release()

atexit.register(cleanup)

if __name__ == "__main__":
    app.run(debug=True)
