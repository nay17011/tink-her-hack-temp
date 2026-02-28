import cv2
import os
import sys
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import create_connection

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- GLOBAL STATE ---
scanning_active = False
selected_subject = "Maths"
present_marked = set()
present_names = set()

# Load OpenCV's built-in face detector (No dlib/face_recognition needed!)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# --- PERIOD DETECTION ---
def get_current_period():
    now = datetime.now().time()
    if now >= datetime.strptime("09:00", "%H:%M").time() and now < datetime.strptime("10:00", "%H:%M").time():
        return "P1"
    elif now >= datetime.strptime("10:00", "%H:%M").time() and now < datetime.strptime("11:00", "%H:%M").time():
        return "P2"
    elif now >= datetime.strptime("11:00", "%H:%M").time() and now < datetime.strptime("12:00", "%H:%M").time():
        return "P3"
    elif now >= datetime.strptime("13:00", "%H:%M").time() and now < datetime.strptime("14:00", "%H:%M").time():
        return "P4"
    return "P5" # Default for testing

# --- ATTENDANCE LOGIC ---
def mark_attendance(name):
    global present_names, present_marked
    period = get_current_period()
    key = f"{name}_{period}_{selected_subject}"
    
    if key in present_marked: return

    now = datetime.now()
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance (name, date, period, subject, time)
        VALUES (?, ?, ?, ?, ?)
    """, (name, now.strftime("%Y-%m-%d"), period, selected_subject, now.strftime("%H:%M:%S")))
    conn.commit()
    conn.close()
    
    present_marked.add(key)
    present_names.add(name)
    print(f"✅ Marked: {name}")

# --- VIDEO STREAMING ---
def gen_frames():
    global scanning_active
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (16, 185, 129), 2)
            
            name = "Student Detected" # In Haar, recognition requires a trained .yml file
            if scanning_active:
                mark_attendance(name)
                cv2.putText(frame, "RECORDING", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- WEB ROUTES ---
@app.route('/')
def home(): return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    id_num, pw = request.form['id_number'], request.form['password']
    if id_num == "admin" and pw == "123":
        session.update({'role': 'admin', 'username': 'admin'})
        return redirect(url_for('admin'))
    return "Invalid Login"

@app.route('/admin')
def admin():
    if session.get('role') != 'admin': return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/attendance')
def attendance():
    if 'role' not in session: return redirect('/')
    return render_template('attendance.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/scanner_control')
def scanner_control():
    global scanning_active
    scanning_active = (request.args.get('status') == 'start')
    return "OK"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)