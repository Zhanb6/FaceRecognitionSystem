import logging
import pickle
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

import numpy as np

try:
    import torch
    from facenet_pytorch import InceptionResnetV1, MTCNN
except ImportError:
    torch = None
    InceptionResnetV1 = None
    MTCNN = None

from PIL import Image

MODEL_ID = "facenet_vggface2_512d"
MODEL_NAME = "vggface2"
DB_FILE = Path("facenet_database.pkl")

CAMERA_INDEX = 0
FACE_INPUT_SIZE = 160
MIN_FACE_SIZE = 80
MIN_DETECTION_CONFIDENCE = 0.90
RECOGNITION_THRESHOLD = 0.70

WINDOW_TITLE = "FaceNet Face Recognition"

logger = logging.getLogger(__name__)


class FaceNetUnavailableError(RuntimeError):
    pass


def ensure_facenet_available():
    missing = []
    if torch is None:
        missing.append("torch")
    if MTCNN is None or InceptionResnetV1 is None:
        missing.append("facenet-pytorch")
    if missing:
        raise FaceNetUnavailableError(
            "FaceNet dependencies are not installed: " + ", ".join(sorted(set(missing)))
        )


def get_device():
    ensure_facenet_available()
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def normalize(vector):
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def load_database(path=DB_FILE):
    if not path.exists():
        return {"__model__": MODEL_ID}

    try:
        with path.open("rb") as file:
            database = pickle.load(file)
    except Exception:
        logger.exception("Could not load database %s", path)
        return {"__model__": MODEL_ID}

    saved_model = database.get("__model__")
    if saved_model != MODEL_ID:
        print(f"Database model mismatch: {saved_model!r} != {MODEL_ID!r}")
        print("Starting with an empty FaceNet database.")
        return {"__model__": MODEL_ID}

    people = get_people(database)
    print(f"Loaded {len(people)} people: {list(people.keys())}")
    return database


def save_database(database, path=DB_FILE):
    with path.open("wb") as file:
        pickle.dump(database, file)


def get_people(database):
    return {name: vectors for name, vectors in database.items() if not name.startswith("__")}


def list_people(database):
    people = get_people(database)
    if not people:
        print("Database is empty.")
        return

    print(f"People in database ({len(people)}):")
    for name, vectors in people.items():
        print(f"  - {name}: {len(vectors)} samples")


def add_person(database, name, embedding, path=DB_FILE):
    database.setdefault(name, [])
    database[name].append(embedding.astype(np.float32))
    save_database(database, path)
    print(f"Enrolled {name}: {len(database[name])} samples")
    return len(database[name])


def delete_person(database, name, path=DB_FILE):
    if name not in database or name.startswith("__"):
        print(f"{name!r} not found.")
        return

    del database[name]
    save_database(database, path)
    print(f"Deleted {name!r}.")


def delete_people_by_prefix(prefix, database_path=DB_FILE):
    database = load_database(database_path)
    deleted = [name for name in get_people(database) if name.startswith(prefix)]
    for name in deleted:
        del database[name]

    if deleted:
        save_database(database, database_path)
    return deleted


def clamp_box(box, width, height):
    x1, y1, x2, y2 = map(int, box)
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def preprocess_face(face_crop):
    face = face_crop.resize((FACE_INPUT_SIZE, FACE_INPUT_SIZE))
    array = np.asarray(face).astype(np.float32)
    array = (array - 127.5) / 128.0
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
    return tensor


def extract_embedding(face_crop, model, device):
    try:
        tensor = preprocess_face(face_crop).to(device)
        with torch.no_grad():
            embedding = model(tensor)[0].cpu().numpy()
        return normalize(embedding)
    except Exception:
        logger.exception("Could not extract FaceNet embedding")
        return None


def recognize_face(embedding, database, threshold=RECOGNITION_THRESHOLD):
    people = get_people(database)
    best_name = "Unknown"
    best_score = 0.0

    for name, samples in people.items():
        for sample in samples:
            score = float(np.dot(embedding, normalize(np.asarray(sample).flatten())))
            if score > best_score:
                best_name = name
                best_score = score

    if best_score < threshold:
        return "Unknown", best_score
    return best_name, best_score


def detect_faces(frame_rgb, detector):
    pil_image = Image.fromarray(frame_rgb)
    boxes, probs = detector.detect(pil_image)
    if boxes is None or probs is None:
        return []

    height, width = frame_rgb.shape[:2]
    detections = []
    for box, prob in zip(boxes, probs):
        if prob < MIN_DETECTION_CONFIDENCE:
            continue

        clamped = clamp_box(box, width, height)
        if clamped is None:
            continue

        detections.append((clamped, float(prob)))

    return detections


@lru_cache(maxsize=1)
def get_facenet_runtime():
    ensure_facenet_available()
    device = get_device()
    detector = MTCNN(keep_all=True, device=device, min_face_size=MIN_FACE_SIZE)
    model = InceptionResnetV1(pretrained=MODEL_NAME).eval().to(device)
    return detector, model, device


def enroll_image_bytes(name, image_bytes, database_path=DB_FILE):
    detector, model, device = get_facenet_runtime()

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    frame_rgb = np.asarray(image)
    detections = detect_faces(frame_rgb, detector)
    if not detections:
        raise ValueError("No face detected")

    best_box, best_prob = max(detections, key=lambda item: item[1])
    x1, y1, x2, y2 = best_box
    face_crop = Image.fromarray(frame_rgb[y1:y2, x1:x2])
    embedding = extract_embedding(face_crop, model, device)
    if embedding is None:
        raise ValueError("Could not compute FaceNet embedding")

    database = load_database(database_path)
    samples = add_person(database, name, embedding, database_path)

    return {
        "embedding": embedding.astype(np.float32),
        "confidence": float(best_prob),
        "box": best_box,
        "samples": samples,
    }


def recognize_image_bytes(image_bytes, database_path=DB_FILE, threshold=RECOGNITION_THRESHOLD):
    detector, model, device = get_facenet_runtime()

    database = load_database(database_path)
    if not get_people(database):
        raise ValueError("FaceNet database is empty")

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    frame_rgb = np.asarray(image)
    detections = detect_faces(frame_rgb, detector)
    if not detections:
        raise ValueError("No face detected")

    best_box, best_prob = max(detections, key=lambda item: item[1])
    x1, y1, x2, y2 = best_box
    face_crop = Image.fromarray(frame_rgb[y1:y2, x1:x2])
    embedding = extract_embedding(face_crop, model, device)
    if embedding is None:
        raise ValueError("Could not compute FaceNet embedding")

    name, score = recognize_face(embedding, database, threshold)
    return {
        "name": name,
        "score": float(score),
        "accuracy": round(max(0.0, min(float(score), 1.0)) * 100, 1),
        "detection_confidence": float(best_prob),
        "box": best_box,
        "recognized": name != "Unknown",
    }


def enroll_from_frame(frame_rgb, detector, model, device, database):
    detections = detect_faces(frame_rgb, detector)
    if not detections:
        print("No face detected for enrollment.")
        return

    name = input("Enter name to enroll: ").strip()
    if not name:
        print("Enrollment cancelled.")
        return

    best_box, best_prob = max(detections, key=lambda item: item[1])
    x1, y1, x2, y2 = best_box
    face_crop = Image.fromarray(frame_rgb[y1:y2, x1:x2])
    embedding = extract_embedding(face_crop, model, device)
    if embedding is None:
        print("Could not compute embedding.")
        return

    add_person(database, name, embedding)
    print(f"Enrollment confidence: {best_prob:.2f}")


def delete_interactive(database):
    list_people(database)
    if not get_people(database):
        return

    name = input("Enter name to delete: ").strip()
    if not name:
        print("Delete cancelled.")
        return

    delete_person(database, name)


def draw_status(frame, fps, database):
    lines = [
        f"FPS: {fps:.1f}",
        f"People: {len(get_people(database))}",
        "E enroll | D delete | L list | Q quit",
    ]

    y = 28
    for line in lines:
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)
        y += 28


def run():
    if cv2 is None:
        print("ERROR: opencv-python is not installed.")
        return

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    device = get_device()
    print(f"Using device: {device}")
    print(f"Loading FaceNet pretrained weights: {MODEL_NAME}")

    detector = MTCNN(keep_all=True, device=device, min_face_size=MIN_FACE_SIZE)
    model = InceptionResnetV1(pretrained=MODEL_NAME).eval().to(device)
    database = load_database()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        return

    print("Controls: E = enroll | D = delete | L = list DB | Q = quit")

    previous_time = time.perf_counter()
    smoothed_fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: Could not read frame.")
                break

            now = time.perf_counter()
            frame_time = now - previous_time
            previous_time = now
            if frame_time > 0:
                fps = 1.0 / frame_time
                smoothed_fps = fps if smoothed_fps == 0 else (0.1 * fps) + (0.9 * smoothed_fps)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detections = detect_faces(frame_rgb, detector)

            for (x1, y1, x2, y2), _prob in detections:
                face_crop = Image.fromarray(frame_rgb[y1:y2, x1:x2])
                embedding = extract_embedding(face_crop, model, device)

                if embedding is None:
                    label = "Embedding error"
                    color = (0, 255, 255)
                else:
                    name, score = recognize_face(embedding, database)
                    label = f"{name} {score:.2f}"
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(25, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            draw_status(frame, smoothed_fps, database)
            cv2.imshow(WINDOW_TITLE, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("e"):
                enroll_from_frame(frame_rgb, detector, model, device, database)
            elif key == ord("d"):
                delete_interactive(database)
            elif key == ord("l"):
                list_people(database)
            elif key == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Done.")


if __name__ == "__main__":
    run()
