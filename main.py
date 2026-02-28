import cv2
import face_recognition
import os
import numpy as np
from datetime import datetime
from database import create_connection
import tkinter as tk
from tkinter import ttk

present_marked = set()
present_names = set()
# =============================
# PERIOD DETECTION
# =============================
def get_current_period():
    now = datetime.now().time()

    if now >= datetime.strptime("09:00", "%H:%M").time() and now < datetime.strptime("10:00", "%H:%M").time():
        return "P1"
    elif now >= datetime.strptime("10:00", "%H:%M").time() and now < datetime.strptime("11:00", "%H:%M").time():
        return "P2"
    elif now >= datetime.strptime("11:00", "%H:%M").time() and now < datetime.strptime("12:00", "%H:%M").time():
        return "P3"

    # 🍱 Lunch break (12–1)
    elif now >= datetime.strptime("13:00", "%H:%M").time() and now < datetime.strptime("14:00", "%H:%M").time():
        return "P4"
    elif now >= datetime.strptime("14:00", "%H:%M").time() and now < datetime.strptime("15:00", "%H:%M").time():
        return "P5"
    elif now >= datetime.strptime("15:00", "%H:%M").time() and now < datetime.strptime("20:00", "%H:%M").time():
        return "P6"
    else:
        return None  # lunch or outside class

present_names = set()



# =============================
# ATTENDANCE FUNCTION
# =============================
def reset_session():
    global present_marked, present_names
    present_marked.clear()
    present_names.clear()
    print("🔄 New class session started")

def mark_attendance(name):
    global present_names

    period = get_current_period()

    if name == "Unknown" or period is None:
        return

    key = f"{name}_{period}_{selected_subject}"

    if key in present_marked:
        return

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time_now = now.strftime("%H:%M:%S")

    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO attendance (name, date, period, subject, time)
    VALUES (?, ?, ?, ?, ?)
    """, (name, date, period, selected_subject, time_now))

    conn.commit()
    conn.close()

    present_marked.add(key)
    present_names.add(name)

    print(f"✅ Attendance marked for {name} — {selected_subject} ({period})")


# =============================
# LOAD DATASET
# =============================
known_encodings = []
known_names = []

dataset_path = "dataset"

for file in os.listdir(dataset_path):
    img_path = os.path.join(dataset_path, file)

    image = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        print(f"⚠️ No face found in {file}, skipping...")
        continue

    known_encodings.append(encodings[0])
    known_names.append(os.path.splitext(file)[0])

print("✅ Dataset loaded successfully!")


# =============================
# SUBJECT SELECTION (MANUAL)
# =============================
def launch_subject_selector():
    def start_attendance():
        global selected_subject
        selected_subject = subject_var.get()
        reset_session()   # ⭐ ADD THIS LINE
        root.destroy()

    root = tk.Tk()
    root.title("Attendance System")
    root.geometry("300x180")
    root.resizable(False, False)

    tk.Label(root, text="Select Subject", font=("Arial", 14, "bold")).pack(pady=10)

    subjects = ["Maths", "Physics", "Chemistry", "Biology", "CS"]
    subject_var = tk.StringVar(value=subjects[0])

    dropdown = ttk.Combobox(root, textvariable=subject_var, values=subjects, state="readonly")
    dropdown.pack(pady=5)

    tk.Button(root, text="Start Attendance", command=start_attendance,
              bg="#4CAF50", fg="white", padx=10, pady=5).pack(pady=15)

    root.mainloop()


launch_subject_selector()
print(f"✅ Subject selected: {selected_subject}")
# =============================
# START WEBCAM
# =============================
video = cv2.VideoCapture(0)
scanning_active = False
while True:
    ret, frame = video.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    # =============================
    # RECOGNITION
    # =============================
    for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):

        name = "Unknown"

        if len(known_encodings) > 0:
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(distances)

            if distances[best_match_index] < 0.5:
                name = known_names[best_match_index]
                
            if scanning_active:   # ⭐ only mark when scanning ON
                mark_attendance(name)
        # draw box + name
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0), 2)
    # =============================
    # LIVE ATTENDANCE DISPLAY
    # =============================
    status_text = "SCANNING ON" if scanning_active else "SCANNING OFF"
    cv2.putText(frame, status_text,
            (20, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255) if not scanning_active else (0, 255, 0),
            2)

    # total present
    cv2.putText(frame, f"Present: {len(present_names)}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2)

    # show names list
    y_offset = 80
    for person in list(present_names)[-5:]:  # show last 5
        cv2.putText(frame, person,
                    (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2)
        y_offset += 30

    cv2.imshow("Face Recognition Attendance", frame)

    # press Q or ESC to exit
    key = cv2.waitKey(1) & 0xFF
    if key == ord("s"):
        scanning_active = True
        print("🟢 Scanning started")
    elif key == ord("p"):
        scanning_active = False
        print("⏸️ Scanning paused")
    elif key == ord("q") or key == 27:
        print("👋 Exiting...")
        break

# =============================
# CLEANUP
# =============================
video.release()
cv2.destroyAllWindows()