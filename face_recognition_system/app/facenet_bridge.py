from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

from .database import BASE_DIR


FACENET_DATABASE = BASE_DIR / "facenet_database.pkl"


class FaceEnrollmentError(RuntimeError):
    pass


class FaceNetDependencyError(FaceEnrollmentError):
    pass


_facenet_module: ModuleType | None = None


def _facenet_script_candidates() -> list[Path]:
    configured_path = os.getenv("FACENET_SCRIPT_PATH")
    candidates = [
        BASE_DIR / "facenet_recognition.py",
        BASE_DIR.parent / "facenet_recognition.py",
        Path.cwd() / "facenet_recognition.py",
        Path.cwd().parent / "facenet_recognition.py",
    ]
    if configured_path:
        candidates.insert(0, Path(configured_path))
    return candidates


def _resolve_facenet_script() -> Path:
    checked_paths = []
    for candidate in _facenet_script_candidates():
        resolved = candidate.resolve()
        checked_paths.append(str(resolved))
        if resolved.exists():
            return resolved
    raise FaceEnrollmentError("FaceNet script not found. Checked: " + ", ".join(checked_paths))


def _load_facenet_module() -> ModuleType:
    global _facenet_module
    if _facenet_module is not None:
        return _facenet_module

    facenet_script = _resolve_facenet_script()
    spec = importlib.util.spec_from_file_location("facenet_recognition_bridge", facenet_script)
    if spec is None or spec.loader is None:
        raise FaceEnrollmentError("Could not load FaceNet script")

    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except ImportError as exc:
        raise FaceNetDependencyError(str(exc)) from exc

    _facenet_module = module
    return module


def available_face_models() -> list[dict]:
    module = _load_facenet_module()
    return module.list_models()


def enroll_face_image(embedding_key: str, image_bytes: bytes) -> dict:
    module = _load_facenet_module()
    try:
        return module.enroll_image_bytes(embedding_key, image_bytes, FACENET_DATABASE)
    except getattr(module, "FaceNetUnavailableError", RuntimeError) as exc:
        raise FaceNetDependencyError(str(exc)) from exc
    except ValueError as exc:
        raise FaceEnrollmentError(str(exc)) from exc


def recognize_face_image(image_bytes: bytes, threshold: float, model_name: str | None = None) -> dict:
    module = _load_facenet_module()
    try:
        return module.recognize_image_bytes(image_bytes, None, threshold, model_name or "efficientnet_lite0")
    except getattr(module, "FaceNetUnavailableError", RuntimeError) as exc:
        raise FaceNetDependencyError(str(exc)) from exc
    except ValueError as exc:
        raise FaceEnrollmentError(str(exc)) from exc


def delete_face_embeddings(face_id: int) -> list[str]:
    module = _load_facenet_module()
    prefix = f"personface:{face_id}:"
    try:
        return module.delete_people_by_prefix(prefix, FACENET_DATABASE)
    except getattr(module, "FaceNetUnavailableError", RuntimeError) as exc:
        raise FaceNetDependencyError(str(exc)) from exc
