import cv2
import os
import numpy as np
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response

# Check if face_recognition is available (since dlib can be tricky)
try:
    import face_recognition
    HAS_FACE_REC = True
except ImportError:
    HAS_FACE_REC = False

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- 1. DATABASE CONNECTION (Integrated from database.py) ---
def get_db_connection():
    # check_same_thread=False is REQUIRED for Flask + OpenCV
    conn = sqlite3.connect("attendance.db", check_same_thread=False)
    return conn

# --- 2. GLOBAL STATE ---
scanning_active = False
selected_subject = "Maths"
present_marked = set()
present_names = set()
known_encodings = []
known_names = []

# --- 3. LOAD DATASET (Recognize your 4 students) ---
def load_dataset():
    global known_encodings, known_names
    dataset_path = "dataset"
    
    if not HAS_FACE_REC:
        print("❌ face_recognition library NOT found. Names will not show.")
        return

    if not os.path.exists(dataset_path):
        print(f"⚠️ Folder '{dataset_path}' not found!")
        return

    for file in os.listdir(dataset_path):
        if file.endswith(('.jpg', '.png', '.jpeg')):
            img_path = os.path.join(dataset_path, file)
            image = face_recognition.load_image_file(img_path)
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(file)[0])
    
    print(f"✅ Successfully loaded {len(known_names)} students: {known_names}")

load_dataset()

# --- 4. PERIOD DETECTION ---
def get_current_period():
    now = datetime.now().time()
    # Using your time logic
    if time_in_range("09:00", "10:00", now): return "P1"
    if time_in_range("10:00", "11:00", now): return "P2"
    if time_in_range("11:00", "12:00", now): return "P3"
    if time_in_range("13:00", "14:00", now): return "P4"
    if time_in_range("14:00", "15:00", now): return "P5"
    return "P6"

def time_in_range(start, end, x):
    s = datetime.strptime(start, "%H:%M").time()
    e = datetime.strptime(end, "%H:%M").time()
    return s <= x <= e

# --- 5. ATTENDANCE LOGIC ---
def mark_attendance(name):
    global present_names, present_marked
    period = get_current_period()
    if name == "Unknown" or not period: return

    key = f"{name}_{period}_{selected_subject}"
    if key in present_marked: return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (name, date, period, subject, time)
            VALUES (?, ?, ?, ?, ?)
        """, (name, datetime.now().strftime("%Y-%m-%d"), period, selected_subject, datetime.now().strftime("%H:%M:%S")))
        conn.commit()
        conn.close()
        
        present_marked.add(key)
        present_names.add(name)
        print(f"✨ Attendance Marked: {name} for {selected_subject}")
    except Exception as e:
        print(f"❌ DB Error: {e}")

# --- 6. VIDEO ENGINE ---
def gen_frames():
    global scanning_active
    camera = cv2.VideoCapture(0)
    
    # Load fallback detector in case face_recognition fails
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    while True:
        success, frame = camera.read()
        if not success: break
        
        if HAS_FACE_REC:
            # High-quality recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name = "Unknown"
                if known_encodings:
                    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_names[best_match_index]

                # Draw UI
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                if scanning_active and name != "Unknown":
                    mark_attendance(name)
                    cv2.putText(frame, "RECORDING...", (left, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        else:
            # Fallback for faster detection if library is missing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame, "Face Detected", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- 7. ROUTES ---
@app.route('/')
def home(): return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    id_num = request.form.get('id_number')
    pw = request.form.get('password')
    if (id_num == "admin" and pw == "123") or (id_num == "student" and pw == "123"):
        session['role'] = id_num
        return redirect(url_for('admin' if id_num == "admin" else 'student'))
    return "Invalid Login"

@app.route('/admin')
def admin():
    if session.get('role') != 'admin': return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/student')
def student():
    if session.get('role') != 'student': return redirect('/')
    return render_template('dashboard.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/scanner_control')
def scanner_control():
    global scanning_active
    scanning_active = (request.args.get('status') == 'start')
    print(f"Scanner Status: {scanning_active}")
    return "OK"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- 8. RUN SERVER ---
if __name__ == '__main__':
    # Use 0.0.0.0 for Render hosting
    port = int(os.environ.get('PORT', 5000))
    # use_reloader=False prevents double-loading the dataset
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)