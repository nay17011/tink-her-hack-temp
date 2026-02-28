from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/attendance", methods=["GET"])
def get_attendance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(dict(row))

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)