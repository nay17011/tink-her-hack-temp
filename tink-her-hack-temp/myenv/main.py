import cv2
import face_recognition
import os
import numpy as np

# -----------------------------
# LOAD DATASET (KNOWN FACES)
# -----------------------------
known_encodings = []
known_names = []

dataset_path = "dataset"

for file in os.listdir(dataset_path):
    img_path = os.path.join(dataset_path, file)

    image = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(image)

    # ✅ IMPORTANT SAFETY CHECK
    if len(encodings) == 0:
        print(f"No face found in {file}, skipping...")
        continue

    known_encodings.append(encodings[0])
    known_names.append(os.path.splitext(file)[0])

print("Dataset loaded successfully!")

# -----------------------------
# START WEBCAM
# -----------------------------
video = cv2.VideoCapture(0)

while True:
    ret, frame = video.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    # -----------------------------
    # RECOGNITION
    # -----------------------------
    for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):

        name = "Unknown"

        if len(known_encodings) > 0:
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(distances)

            if distances[best_match_index] < 0.5:  # 🔥 tolerance (important)
                name = known_names[best_match_index]

        # Draw box + name
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0), 2)

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video.release()
cv2.destroyAllWindows()