from flask import Flask, render_template, request, redirect, url_for, session, Response
import cv2
import face_recognition
import os
import numpy as np
from datetime import datetime
from database import create_connection # Ensure database.py is in the same folder

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- GLOBAL STATE ---
scanning_active = False
selected_subject = "Maths"
present_marked = set()
present_names = set()

# --- LOAD DATASET (Move this from facerecognition.py) ---
known_encodings = []
known_names = []
dataset_path = "dataset"

if os.path.exists(dataset_path):
    for file in os.listdir(dataset_path):
        img_path = os.path.join(dataset_path, file)
        image = face_recognition.load_image_file(img_path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(os.path.splitext(file)[0])
    print(f"✅ Loaded {len(known_names)} faces.")

# --- SHARED FUNCTIONS ---
def get_current_period():
    now = datetime.now().time()
    # Simplified for brevity; keep your original logic here
    if now >= datetime.strptime("09:00", "%H:%M").time() and now < datetime.strptime("10:00", "%H:%M").time():
        return "P1"
    # ... add your other periods ...
    return "P6" # Fallback for testing

def mark_attendance_db(name):
    global present_names, present_marked
    period = get_current_period()
    if name == "Unknown" or period is None: return
    
    key = f"{name}_{period}_{selected_subject}"
    if key in present_marked: return

    now = datetime.now()
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance (name, date, period, subject, time) VALUES (?, ?, ?, ?, ?)",
                   (name, now.strftime("%Y-%m-%d"), period, selected_subject, now.strftime("%H:%M:%S")))
    conn.commit()
    conn.close()
    present_marked.add(key)
    present_names.add(name)

# --- VIDEO STREAM GENERATOR ---
def gen_frames():
    global scanning_active
    video = cv2.VideoCapture(0)
    while True:
        success, frame = video.read()
        if not success: break
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            name = "Unknown"
            if known_encodings:
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                if np.min(distances) < 0.5:
                    name = known_names[np.argmin(distances)]
                    if scanning_active:
                        mark_attendance_db(name)

            cv2.rectangle(frame, (left, top), (right, bottom), (16, 185, 129), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# --- ROUTES ---
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/scanner_control')
def scanner_control():
    global scanning_active
    scanning_active = (request.args.get('status') == 'start')
    return "OK"

@app.route('/update_subject')
def update_subject():
    global selected_subject, present_marked, present_names
    selected_subject = request.args.get('subject')
    present_marked.clear()
    present_names.clear()
    return "OK"

# ... Keep your existing @app.route('/') through @app.route('/logout') ...

@app.route('/attendance')
def attendance():
    if 'role' not in session: return redirect('/')
    return render_template('attendance.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)