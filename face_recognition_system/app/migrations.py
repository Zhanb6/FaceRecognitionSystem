from sqlalchemy import inspect, text

from .database import engine


def ensure_schema_updates() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "face_enrollments" in table_names:
        face_enrollment_columns = {
            column["name"] for column in inspector.get_columns("face_enrollments")
        }
        if "person_name" not in face_enrollment_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE face_enrollments ADD COLUMN person_name VARCHAR(255) DEFAULT ''"))
                connection.execute(text("""
                    UPDATE face_enrollments
                    SET person_name = COALESCE((
                        SELECT person_faces.full_name
                        FROM person_faces
                        WHERE person_faces.id = face_enrollments.person_id
                    ), '')
                    WHERE person_name IS NULL OR person_name = ''
                """))

    if "recognition_logs" not in table_names:
        return

    recognition_log_columns = {
        column["name"] for column in inspector.get_columns("recognition_logs")
    }
    recognition_log_updates = {
        "model_name": "VARCHAR(100) DEFAULT 'EfficientNet-Lite0'",
        "processing_time_ms": "FLOAT DEFAULT 0",
        "average_fps": "FLOAT DEFAULT 0",
        "energy_consumption_wh": "FLOAT DEFAULT 0",
    }
    with engine.begin() as connection:
        for column_name, column_type in recognition_log_updates.items():
            if column_name not in recognition_log_columns:
                connection.execute(text(f"ALTER TABLE recognition_logs ADD COLUMN {column_name} {column_type}"))
