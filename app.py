from datetime import datetime

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash

from database import fetch_employee_by_code, fetch_user_by_username, get_connection, init_db
from face_utils import FACE_DIR, recognize_face_from_data_url, save_face_from_data_url

app = Flask(__name__)
app.secret_key = 'replace-with-a-secure-secret-key'


@app.before_request
def bootstrap_db():
    init_db()


@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''

    user = fetch_user_by_username(username)
    if user is not None and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('dashboard'))

    flash('Invalid username or password.', 'error')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('index'))

    conn = get_connection()
    total_employees = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    today_count = conn.execute("SELECT COUNT(*) FROM attendance WHERE date(check_in_at) = date('now')").fetchone()[0]
    recent_logs = conn.execute(
        '''
        SELECT a.*, e.name, e.employee_code, e.department
        FROM attendance a
        INNER JOIN students e ON e.id = a.employee_id
        ORDER BY a.created_at DESC
        LIMIT 10
        '''
    ).fetchall()
    conn.close()

    return render_template('dashboard.html', total_employees=total_employees, today_count=today_count, recent_logs=recent_logs)


@app.route('/employees', methods=['GET', 'POST'], endpoint='employees')
@app.route('/students', methods=['GET', 'POST'], endpoint='students')
def employees():
    if not session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        employee_code = (request.form.get('employee_code') or '').strip()
        email = (request.form.get('email') or '').strip()
        department = (request.form.get('department') or '').strip()
        photo = request.form.get('photo') or ''

        if not name or not employee_code:
            flash('Name and employee code are required.', 'error')
            return redirect(url_for('employees'))
        if not photo:
            flash('A face photo is required.', 'error')
            return redirect(url_for('employees'))

        conn = get_connection()
        existing = conn.execute('SELECT id FROM students WHERE employee_code = ? LIMIT 1', (employee_code,)).fetchone()
        if existing:
            conn.close()
            flash('Employee code already exists.', 'error')
            return redirect(url_for('employees'))

        try:
            saved_path = save_face_from_data_url(photo, employee_code)
            conn.execute(
                'INSERT INTO students (employee_code, name, email, department, photo_path) VALUES (?, ?, ?, ?, ?)',
                (employee_code, name, email, department, saved_path),
            )
            conn.commit()
            flash('Employee saved successfully.', 'success')
        except Exception as exc:
            flash(str(exc), 'error')
        finally:
            conn.close()

        return redirect(url_for('employees'))

    conn = get_connection()
    students_list = conn.execute('SELECT * FROM students ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('students.html', students=students_list)


@app.get('/employee-faces/<path:filename>')
def employee_face(filename):
    if not session.get('user_id'):
        abort(404)
    return send_from_directory(FACE_DIR, filename)


@app.route('/attendance')
def attendance():
    if not session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('attendance.html')


@app.route('/attendance/success')
def attendance_success():
    if not session.get('user_id'):
        return redirect(url_for('index'))

    attendance_result = session.pop('attendance_success', None)
    if attendance_result is None:
        return redirect(url_for('attendance'))
    return render_template('attendance_success.html', result=attendance_result)


@app.route('/api/recognize-face', methods=['POST'])
def api_recognize_face():
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    photo = payload.get('photo') or ''
    if not photo:
        return jsonify({'success': False, 'message': 'No face image was submitted.'}), 400

    try:
        employee_code = recognize_face_from_data_url(photo)
        employee = fetch_employee_by_code(employee_code)
        if employee is None:
            return jsonify({'success': False, 'message': 'Employee record not found.'}), 404

        conn = get_connection()
        today_record = conn.execute(
            "SELECT check_in_at, check_out_at FROM attendance WHERE employee_id = ? AND date(check_in_at) = date('now') ORDER BY check_in_at DESC LIMIT 1",
            (employee['id'],),
        ).fetchone()
        conn.close()

        return jsonify({
            'success': True,
            'employee_id': employee['id'],
            'employee_code': employee['employee_code'],
            'name': employee['name'],
            'can_check_in': today_record is None,
            'can_check_out': today_record is not None and today_record['check_out_at'] is None,
        })
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@app.route('/api/mark-attendance', methods=['POST'])
def api_mark_attendance():
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    try:
        employee_id = int(payload.get('employee_id') or 0)
    except (TypeError, ValueError):
        employee_id = 0
    action = payload.get('action')
    if employee_id <= 0:
        return jsonify({'success': False, 'message': 'Employee is required.'}), 400
    if action not in {'check-in', 'check-out'}:
        return jsonify({'success': False, 'message': 'Choose check-in or check-out.'}), 400

    conn = get_connection()
    employee = conn.execute(
        'SELECT id, name, employee_code FROM students WHERE id = ? LIMIT 1',
        (employee_id,),
    ).fetchone()
    if employee is None:
        conn.close()
        return jsonify({'success': False, 'message': 'Employee record not found.'}), 404

    marked_at = datetime.now()
    record = conn.execute(
        "SELECT * FROM attendance WHERE employee_id = ? AND check_in_at IS NOT NULL AND check_out_at IS NULL AND date(check_in_at) = date('now') LIMIT 1",
        (employee_id,),
    ).fetchone()

    if action == 'check-in':
        if record:
            conn.close()
            return jsonify({'success': False, 'message': 'This employee is already checked in today.'}), 409

        completed_record = conn.execute(
            "SELECT 1 FROM attendance WHERE employee_id = ? AND date(check_in_at) = date('now') LIMIT 1",
            (employee_id,),
        ).fetchone()
        if completed_record:
            conn.close()
            return jsonify({'success': False, 'message': 'Attendance is already complete for this employee today.'}), 409

        conn.execute(
            'INSERT INTO attendance (employee_id, check_in_at, status) VALUES (?, ?, ?)',
            (employee_id, marked_at.strftime('%Y-%m-%d %H:%M:%S'), 'present'),
        )
    else:
        if not record:
            conn.close()
            return jsonify({'success': False, 'message': 'No open check-in was found for this employee today.'}), 409

        check_out_at = marked_at.strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE attendance SET check_out_at = ? WHERE id = ?', (check_out_at, record['id']))

    conn.commit()
    conn.close()

    session['attendance_success'] = {
        'employee_name': employee['name'],
        'employee_code': employee['employee_code'],
        'action': action,
        'marked_at': marked_at.strftime('%Y-%m-%d %H:%M:%S'),
    }
    return jsonify({'success': True, 'message': f'Attendance {action} recorded.'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
