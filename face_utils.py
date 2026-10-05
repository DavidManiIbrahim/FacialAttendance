import base64
import os

try:
    import face_recognition
except ImportError:  # pragma: no cover
    face_recognition = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_DIR = os.path.join(BASE_DIR, 'uploads', 'faces')
FACE_FILENAME_PREFIX = 'student-'


def ensure_face_dir():
    os.makedirs(FACE_DIR, exist_ok=True)


def face_filename_stem(employee_code):
    encoded_code = base64.urlsafe_b64encode(employee_code.encode('utf-8')).decode('ascii').rstrip('=')
    return FACE_FILENAME_PREFIX + encoded_code


def employee_code_from_face_filename(stem):
    if not stem.startswith(FACE_FILENAME_PREFIX):
        return stem

    encoded_code = stem[len(FACE_FILENAME_PREFIX):]
    padding = '=' * (-len(encoded_code) % 4)
    return base64.urlsafe_b64decode(encoded_code + padding).decode('utf-8')


def save_face_from_data_url(data_url, employee_code):
    if not data_url or 'data:image' not in data_url:
        raise ValueError('A valid face image is required.')

    header, data = data_url.split(',', 1)
    if 'image/png' in header:
        ext = 'png'
    elif 'image/jpeg' in header or 'image/jpg' in header:
        ext = 'jpg'
    else:
        ext = 'png'

    image_bytes = base64.b64decode(data)
    ensure_face_dir()
    filename_stem = face_filename_stem(employee_code)
    file_path = os.path.join(FACE_DIR, f'{filename_stem}.{ext}')

    with open(file_path, 'wb') as photo_file:
        photo_file.write(image_bytes)

    return f'uploads/faces/{filename_stem}.{ext}'


def recognize_face_from_data_url(data_url):
    if face_recognition is None:
        raise RuntimeError('Install the face-recognition package first: pip install face-recognition opencv-python')

    if not data_url or 'data:image' not in data_url:
        raise ValueError('No face image was provided.')

    header, data = data_url.split(',', 1)
    if 'image/png' in header:
        ext = 'png'
    elif 'image/jpeg' in header or 'image/jpg' in header:
        ext = 'jpg'
    else:
        ext = 'png'

    working = os.path.join(BASE_DIR, 'tmp_face_capture.' + ext)
    with open(working, 'wb') as tmp_file:
        tmp_file.write(base64.b64decode(data))

    try:
        source_image = face_recognition.load_image_file(working)
        source_encoding = face_recognition.face_encodings(source_image)
        if not source_encoding:
            raise ValueError('No face was detected in the submitted image.')

        source_encoding = source_encoding[0]
        known_encodings = []
        known_codes = []

        if os.path.isdir(FACE_DIR):
            for filename in sorted(os.listdir(FACE_DIR)):
                full_path = os.path.join(FACE_DIR, filename)
                if not os.path.isfile(full_path):
                    continue
                name, extension = os.path.splitext(filename)
                if extension.lower() not in {'.png', '.jpg', '.jpeg'}:
                    continue
                try:
                    image = face_recognition.load_image_file(full_path)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        known_encodings.append(encodings[0])
                        known_codes.append(employee_code_from_face_filename(name))
                except Exception:
                    continue

        if not known_encodings:
            raise ValueError('No employee face samples are available for matching.')

        best_match = None
        best_distance = 1.0
        matches = face_recognition.compare_faces(known_encodings, source_encoding, tolerance=0.5)
        for index, matched in enumerate(matches):
            if not matched:
                continue
            distances = face_recognition.face_distance([known_encodings[index]], source_encoding)
            score = float(distances[0])
            if score < best_distance:
                best_distance = score
                best_match = known_codes[index]

        if best_match is None:
            raise ValueError('No matching employee face was found.')

        return best_match
    finally:
        if os.path.exists(working):
            os.remove(working)
