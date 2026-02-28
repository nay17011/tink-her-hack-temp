from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecretkey"   # REQUIRED for session to work


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    id_number = request.form['id_number']
    password = request.form['password']

    if id_number == "admin" and password == "123":
        session['role'] = 'admin'
        session['username'] = 'admin'
        return redirect(url_for('admin'))

    elif id_number == "student" and password == "123":
        session['role'] = 'student'
        session['username'] = 'student'
        return redirect(url_for('student'))

    else:
        return "Invalid Login"


@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('admin_dashboard.html')


@app.route('/student')
def student():
    if session.get('role') != 'student':
        return redirect('/')
    return render_template('dashboard.html')


@app.route('/attendance')
def attendance():
    if 'role' not in session:
        return redirect('/')
    return render_template('attendance.html')


@app.route('/profile')
def profile():
    if 'role' not in session:
        return redirect('/')

    if session['role'] == 'admin':
        return render_template('profile.html')   # your admin profile file

    elif session['role'] == 'student':
        return render_template('student_profile.html')


@app.route('/report')
def report():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('report.html')


@app.route('/student_details')
def student_details():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('student_details_1.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/take_attendance')
def take_attendance():
    if session.get('role') != 'admin':
        return redirect('/')

    print("Attendance button clicked")
    return "Attendance process started"


if __name__ == '__main__':
    app.run(debug=True)