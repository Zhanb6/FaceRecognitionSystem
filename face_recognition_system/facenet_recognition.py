from __future__ import annotations

import logging
import pickle
import sys
import time
from dataclasses import dataclass
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


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_FILE = BASE_DIR / "facenet_database.pkl"
CAMERA_INDEX = 0
MIN_FACE_SIZE = 80
MIN_DETECTION_CONFIDENCE = 0.90
RECOGNITION_THRESHOLD = 0.70
WINDOW_TITLE = "Multi-model Face Recognition"

logger = logging.getLogger(__name__)


class FaceNetUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeConfig:
    key: str
    label: str
    model_id: str
    input_size: int
    embedding_size: int
    database_path: Path
    checkpoint_path: Path | None
    power_watts: float


MODEL_CONFIGS = {
    "facenet": RuntimeConfig(
        key="facenet",
        label="FaceNet",
        model_id="facenet_vggface2_512d",
        input_size=160,
        embedding_size=512,
        database_path=DB_FILE,
        checkpoint_path=None,
        power_watts=18.0,
    ),
    "mobilefacenet": RuntimeConfig(
        key="mobilefacenet",
        label="MobileFaceNet",
        model_id="mobilefacenet_128d",
        input_size=112,
        embedding_size=128,
        database_path=BASE_DIR / "mobilefacenet_database.pkl",
        checkpoint_path=BASE_DIR / "experiments" / "mobilefacenet" / "best.pt",
        power_watts=6.0,
    ),
    "efficientnet_lite0": RuntimeConfig(
        key="efficientnet_lite0",
        label="EfficientNet-Lite0",
        model_id="efficientnet_lite0_512d",
        input_size=112,
        embedding_size=512,
        database_path=BASE_DIR / "efficientnet_lite0_database.pkl",
        checkpoint_path=BASE_DIR / "experiments" / "efficientnet_lite0" / "best.pt",
        power_watts=9.0,
    ),
}
MODEL_ALIASES = {
    "facenet-cpu": "facenet",
    "facenet-gpu": "facenet",
    "efficientnet-lite0": "efficientnet_lite0",
    "efficientnet": "efficientnet_lite0",
}


def normalize_model_name(model_name=None):
    key = (model_name or "efficientnet_lite0").strip().lower()
    key = MODEL_ALIASES.get(key, key)
    if key not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model '{model_name}'. Available models: {', '.join(MODEL_CONFIGS)}")
    return key


def list_models():
    return [
        {
            "key": config.key,
            "label": config.label,
            "input_size": config.input_size,
            "embedding_size": config.embedding_size,
            "database_path": str(config.database_path),
            "checkpoint_path": str(config.checkpoint_path) if config.checkpoint_path else None,
        }
        for config in MODEL_CONFIGS.values()
    ]


def ensure_facenet_available():
    missing = []
    if torch is None:
        missing.append("torch")
    if MTCNN is None or InceptionResnetV1 is None:
        missing.append("facenet-pytorch")
    if missing:
        raise FaceNetUnavailableError(
            "Face recognition dependencies are not installed: " + ", ".join(sorted(set(missing)))
        )


def get_device():
    ensure_facenet_available()
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def normalize(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def get_people(database):
    return {name: vectors for name, vectors in database.items() if not name.startswith("__")}


def load_database(path=DB_FILE, model_name=None):
    model_key = normalize_model_name(model_name) if model_name else "facenet"
    config = MODEL_CONFIGS[model_key]
    path = Path(path) if path is not None else config.database_path

    if not path.exists():
        return {"__model__": config.model_id, "__backbone__": config.key}

    try:
        with path.open("rb") as file:
            database = pickle.load(file)
    except Exception:
        logger.exception("Could not load database %s", path)
        return {"__model__": config.model_id, "__backbone__": config.key}

    saved_model = database.get("__model__")
    if saved_model != config.model_id:
        print(f"Database model mismatch in {path}: {saved_model!r} != {config.model_id!r}")
        print(f"Starting with an empty {config.label} database.")
        return {"__model__": config.model_id, "__backbone__": config.key}

    database.setdefault("__backbone__", config.key)
    people = get_people(database)
    print(f"Loaded {len(people)} people for {config.label}: {list(people.keys())}")
    return database


def save_database(database, path=DB_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        pickle.dump(database, file)


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


def delete_people_by_prefix(prefix, database_path=None, model_name=None):
    model_keys = [normalize_model_name(model_name)] if model_name else list(MODEL_CONFIGS)
    deleted = []
    for model_key in model_keys:
        config = MODEL_CONFIGS[model_key]
        path = Path(database_path) if database_path and model_name else config.database_path
        database = load_database(path, model_key)
        deleted_for_model = [name for name in get_people(database) if name.startswith(prefix)]
        for name in deleted_for_model:
            del database[name]

        if deleted_for_model:
            save_database(database, path)
        deleted.extend(f"{model_key}:{name}" for name in deleted_for_model)
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


def preprocess_face(face_crop, input_size):
    face = face_crop.resize((input_size, input_size))
    array = np.asarray(face).astype(np.float32)
    array = (array / 255.0 - 0.5) / 0.5
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
    return tensor


def _build_model(config):
    if config.key == "facenet":
        return InceptionResnetV1(pretrained="vggface2")
    if config.key == "mobilefacenet":
        from face_models.mobilefacenet import MobileFaceNet

        return MobileFaceNet(embedding_size=config.embedding_size, input_size=config.input_size)
    if config.key == "efficientnet_lite0":
        from face_models.efficientnet_lite import EfficientNetLite0Face

        return EfficientNetLite0Face(embedding_size=config.embedding_size, pretrained=False)
    raise ValueError(f"Unknown model '{config.key}'")


@lru_cache(maxsize=len(MODEL_CONFIGS))
def get_model_runtime(model_name="efficientnet_lite0"):
    ensure_facenet_available()
    model_key = normalize_model_name(model_name)
    config = MODEL_CONFIGS[model_key]
    device = get_device()
    try:
        model = _build_model(config).eval().to(device)
    except Exception as exc:
        raise FaceNetUnavailableError(f"Could not load {config.label}: {exc}") from exc

    if config.checkpoint_path:
        if not config.checkpoint_path.exists():
            raise FaceNetUnavailableError(f"Checkpoint not found: {config.checkpoint_path}")
        try:
            checkpoint = torch.load(config.checkpoint_path, map_location="cpu")
            checkpoint_model = checkpoint.get("model_name")
            if checkpoint_model and checkpoint_model != config.key:
                raise FaceNetUnavailableError(
                    f"Checkpoint model '{checkpoint_model}' does not match '{config.key}'"
                )
            model.load_state_dict(checkpoint["model_state_dict"])
        except FaceNetUnavailableError:
            raise
        except Exception as exc:
            raise FaceNetUnavailableError(f"Could not load {config.label} checkpoint: {exc}") from exc
        model.eval().to(device)

    return model, device, config


@lru_cache(maxsize=1)
def get_detector():
    ensure_facenet_available()
    return MTCNN(keep_all=True, device=get_device(), min_face_size=MIN_FACE_SIZE)


def extract_embedding(face_crop, model, device, input_size):
    try:
        tensor = preprocess_face(face_crop, input_size).to(device)
        with torch.no_grad():
            embedding = model(tensor)[0].cpu().numpy()
        return normalize(embedding)
    except Exception:
        logger.exception("Could not extract face embedding")
        return None


def recognize_face(embedding, database, threshold=RECOGNITION_THRESHOLD):
    people = get_people(database)
    best_name = "Unknown"
    best_score = 0.0

    for name, samples in people.items():
        for sample in samples:
            sample_vector = normalize(np.asarray(sample).flatten())
            if sample_vector.shape != embedding.shape:
                continue
            score = float(np.dot(embedding, sample_vector))
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


def _best_face_crop(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    frame_rgb = np.asarray(image)
    detections = detect_faces(frame_rgb, get_detector())
    if not detections:
        raise ValueError("No face detected")

    best_box, best_prob = max(detections, key=lambda item: item[1])
    x1, y1, x2, y2 = best_box
    return Image.fromarray(frame_rgb[y1:y2, x1:x2]), best_box, best_prob


def enroll_image_bytes(name, image_bytes, database_path=None, model_name=None):
    face_crop, best_box, best_prob = _best_face_crop(image_bytes)
    model_keys = [normalize_model_name(model_name)] if model_name else list(MODEL_CONFIGS)
    results = {}

    for model_key in model_keys:
        model, device, config = get_model_runtime(model_key)
        embedding = extract_embedding(face_crop, model, device, config.input_size)
        if embedding is None:
            raise ValueError(f"Could not compute {config.label} embedding")

        path = Path(database_path) if database_path and model_name else config.database_path
        database = load_database(path, model_key)
        samples = add_person(database, name, embedding, path)
        results[model_key] = {
            "model_name": config.label,
            "embedding": embedding.astype(np.float32),
            "samples": samples,
        }

    primary_key = model_keys[0]
    primary = results[primary_key]
    return {
        "embedding": primary["embedding"],
        "confidence": float(best_prob),
        "box": best_box,
        "samples": primary["samples"],
        "models": {
            key: {"model_name": value["model_name"], "samples": value["samples"]}
            for key, value in results.items()
        },
    }


def recognize_image_bytes(image_bytes, database_path=None, threshold=RECOGNITION_THRESHOLD, model_name="efficientnet_lite0"):
    model_key = normalize_model_name(model_name)
    model, device, config = get_model_runtime(model_key)
    path = Path(database_path) if database_path and model_name else config.database_path
    database = load_database(path, model_key)
    if not get_people(database):
        raise ValueError(f"{config.label} database is empty")

    face_crop, best_box, best_prob = _best_face_crop(image_bytes)
    embedding = extract_embedding(face_crop, model, device, config.input_size)
    if embedding is None:
        raise ValueError(f"Could not compute {config.label} embedding")

    name, score = recognize_face(embedding, database, threshold)
    return {
        "name": name,
        "score": float(score),
        "accuracy": round(max(0.0, min(float(score), 1.0)) * 100, 1),
        "detection_confidence": float(best_prob),
        "box": best_box,
        "recognized": name != "Unknown",
        "model_key": config.key,
        "model_name": config.label,
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
    embedding = extract_embedding(face_crop, model, device, MODEL_CONFIGS["facenet"].input_size)
    if embedding is None:
        print("Could not compute embedding.")
        return

    add_person(database, name, embedding, MODEL_CONFIGS["facenet"].database_path)
    print(f"Enrollment confidence: {best_prob:.2f}")


def list_people(database):
    people = get_people(database)
    if not people:
        print("Database is empty.")
        return

    print(f"People in database ({len(people)}):")
    for name, vectors in people.items():
        print(f"  - {name}: {len(vectors)} samples")


def delete_interactive(database):
    list_people(database)
    if not get_people(database):
        return

    name = input("Enter name to delete: ").strip()
    if not name:
        print("Delete cancelled.")
        return

    delete_person(database, name, MODEL_CONFIGS["facenet"].database_path)


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
    print("Loading FaceNet pretrained weights: vggface2")

    detector = get_detector()
    model, device, config = get_model_runtime("facenet")
    database = load_database(config.database_path, config.key)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        return

    print("Controls: E = enroll | D = delete | L list DB | Q quit")

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
                embedding = extract_embedding(face_crop, model, device, config.input_size)

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
