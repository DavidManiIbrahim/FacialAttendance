#!/usr/bin/env python3
import argparse
import json
import os
import sys

try:
    import face_recognition
except ImportError:
    print(json.dumps({
        'success': False,
        'message': 'face_recognition is not installed. Run: py -m pip install face-recognition opencv-python'
    }))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Match an uploaded face against known employee photos.')
    parser.add_argument('--source', required=True, help='Path to the uploaded face image')
    parser.add_argument('--known-dir', required=True, help='Directory containing employee reference photos')
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(json.dumps({'success': False, 'message': 'Source image not found.'}))
        return 1

    if not os.path.isdir(args.known_dir):
        print(json.dumps({'success': False, 'message': 'Known faces directory not found.'}))
        return 1

    source_image = face_recognition.load_image_file(args.source)
    source_encodings = face_recognition.face_encodings(source_image)

    if not source_encodings:
        print(json.dumps({'success': False, 'message': 'No face was detected in the submitted image.'}))
        return 1

    source_encoding = source_encodings[0]
    known_face_names = []
    known_face_encodings = []

    for filename in sorted(os.listdir(args.known_dir)):
        name, ext = os.path.splitext(filename)
        if ext.lower() not in {'.png', '.jpg', '.jpeg', '.bmp'}:
            continue
        path = os.path.join(args.known_dir, filename)
        try:
            face_image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(face_image)
            if not encodings:
                continue
            known_face_names.append(name)
            known_face_encodings.append(encodings[0])
        except Exception:
            continue

    if not known_face_encodings:
        print(json.dumps({'success': False, 'message': 'No reference face images were found.'}))
        return 1

    matches = face_recognition.compare_faces(known_face_encodings, source_encoding, tolerance=0.5)
    best_match_index = None
    best_match_distance = 1.0

    for idx, matched in enumerate(matches):
        if not matched:
            continue
        distances = face_recognition.face_distance([known_face_encodings[idx]], source_encoding)
        value = float(distances[0])
        if value < best_match_distance:
            best_match_distance = value
            best_match_index = idx

    if best_match_index is None:
        print(json.dumps({'success': False, 'message': 'No matching employee face was found.'}))
        return 1

    print(json.dumps({
        'success': True,
        'employee_code': known_face_names[best_match_index],
        'confidence': round(1 - best_match_distance, 4)
    }))
    return 0


if __name__ == '__main__':
    sys.exit(main())
