from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import uuid

app = Flask(__name__)
app.secret_key = 'b2e07e5f8a1749c4b88b1f38d85e34db345d88204a6e7105c9cf6ce562f50cda'

# === In-memory mock data === #
users = {}  # key: email
appointments = []

# === Helper Functions === #
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'doctor':
            flash('Doctor access only', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# === Routes === #
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if email in users:
            flash("User already exists.", "error")
            return redirect(url_for('register'))

        user_id = str(uuid.uuid4())
        user_type = request.form['user_type']
        user = {
            'user_id': user_id,
            'name': request.form['name'],
            'email': email,
            'phone': request.form['phone'],
            'password': hash_password(request.form['password']),
            'user_type': user_type,
            'created_at': datetime.now().isoformat()
        }

        if user_type == 'doctor':
            user['specialization'] = request.form['specialization']
            user['license_number'] = request.form['license_number']

        users[email] = user
        flash("Registration successful. Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        user = users.get(email)
        if user and user['password'] == hash_password(password) and user['user_type'] == user_type:
            session['user_id'] = user['user_id']
            session['user_type'] = user['user_type']
            session['name'] = user['name']
            session['email'] = user['email']
            if user_type == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash("Invalid credentials", "error")

    return render_template('login.html')

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if session['user_type'] != 'patient':
        return redirect(url_for('login'))

    upcoming = []
    past = []
    now = datetime.now()

    for apt in appointments:
        if apt['patient_id'] == session['user_id']:
            apt_time = datetime.fromisoformat(apt['appointment_datetime'])
            if apt_time > now:
                upcoming.append(apt)
            else:
                past.append(apt)

    return render_template('patient_dashboard.html', 
                           upcoming_appointments=upcoming,
                           past_appointments=past)

@app.route('/doctor/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    today = datetime.now().date()
    today_apts = []
    upcoming_apts = []

    for apt in appointments:
        if apt['doctor_id'] == session['user_id']:
            apt_date = datetime.fromisoformat(apt['appointment_datetime']).date()
            if apt_date == today:
                today_apts.append(apt)
            elif apt_date > today:
                upcoming_apts.append(apt)

    return render_template('doctor_dashboard.html',
                           today_appointments=today_apts,
                           upcoming_appointments=upcoming_apts)

@app.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if session['user_type'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        doc_id = request.form['doctor_id']
        doctor = next((u for u in users.values() if u['user_id'] == doc_id), None)
        if not doctor:
            flash("Doctor not found", "error")
            return redirect(url_for('book_appointment'))

        apt = {
            'appointment_id': str(uuid.uuid4()),
            'patient_id': session['user_id'],
            'patient_name': session['name'],
            'doctor_id': doctor['user_id'],
            'doctor_name': doctor['name'],
            'appointment_datetime': request.form['appointment_datetime'],
            'reason': request.form['reason'],
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        appointments.append(apt)
        flash("Appointment booked successfully!", "success")
        return redirect(url_for('patient_dashboard'))

    # List of available doctors
    doctor_list = [u for u in users.values() if u['user_type'] == 'doctor']
    return render_template('book_appointment.html', doctors=doctor_list)

@app.route('/appointment-history')
@login_required
def appointment_history():
    user_id = session['user_id']
    role = session['user_type']
    user_appointments = []

    for apt in appointments:
        if (role == 'patient' and apt['patient_id'] == user_id) or \
           (role == 'doctor' and apt['doctor_id'] == user_id):
            user_appointments.append(apt)

    return render_template('appointment_history.html', appointments=user_appointments)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
