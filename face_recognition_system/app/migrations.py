from sqlalchemy import inspect, text

from .database import engine


def ensure_schema_updates() -> None:
    inspector = inspect(engine)
    if "face_enrollments" not in inspector.get_table_names():
        return

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
