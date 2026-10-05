# Facial Attendance System

A local web application for student enrollment and attendance using Python, Flask, SQLite, HTML, and webcam-based face matching.

## Requirements

- Python 3.10 or newer
- A modern browser with webcam access
- Windows, macOS, or Linux

The face-matching dependency uses `dlib` through `face_recognition`. The Windows commands below use a prebuilt `dlib-bin` wheel, avoiding a local C++ build.

## Install on Windows

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install "setuptools<81" dlib-bin==20.0.1 face-recognition-models==0.3.0
python -m pip install face-recognition==1.3.0 --no-deps
```

If PowerShell blocks virtual-environment activation, run `python -m pip install -r requirements.txt` without activating it, using the same Python installation.

## Install on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install face-recognition==1.3.0
```

## Start the application

From the project folder, with the virtual environment active:

```bash
python app.py
```

Open <http://127.0.0.1:5000> in your browser. Webcam access is available on localhost; allow the browser to use your camera when prompted.

## Sign in

The first run creates the SQLite database and a default administrator account:

- Username: `admin`
- Password: `admin123`

Change the default credentials and Flask secret key before using the app beyond local testing. The secret key is configured in `app.py`.

## Use the app

1. Sign in to the dashboard.
2. Open **Students**, enter the student details, start the camera, capture a face, and save the student.
3. Open **Attendance**, start the camera, and identify the student using the webcam.
4. After the match, choose **Check in** or **Check out**. Only the action valid for that student's attendance state is enabled.
5. After attendance is saved, the app shows a confirmation page with the student and recorded time. Review recent records on the dashboard.

## Project layout

- `app.py` — Flask routes and application entry point
- `database.py` — SQLite connection and initialization
- `schema.sql` — `users`, `students`, and `attendance` table definitions
- `face_utils.py` — face image storage and recognition
- `templates/` — HTML pages rendered by Flask
- `static/` — CSS and static images
- `uploads/faces/` — student face images
- `database/attendance.db` — generated SQLite database
- `/students` — student enrollment and directory page (`/employees` remains as a legacy alias)
- `/attendance` — face identification and separate check-in/check-out actions

## Troubleshooting

- **Python command not found:** install Python and enable the option to add it to `PATH`, then reopen PowerShell.
- **Camera unavailable:** use `localhost` or `127.0.0.1` and grant camera permission in the browser.
- **Face-recognition installation fails:** check that your Python version is supported by the available `dlib` wheels, or install the platform's required C++ build tools before retrying.
- **No face match:** make sure the employee was enrolled with a clear, front-facing image and the camera has adequate lighting.

This project is intended as a local starter application. Face images are biometric data; obtain appropriate consent and protect stored images and records before deploying it for real students.
