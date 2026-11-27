"""Initialize a fresh configured deployment database; never drop or reseed existing data."""
from .database import OWNER_MARKER, SQL_DIRECTORY, check_schema, environment_engine, schema_marker


def initialize_database(connection):
    existing = schema_marker(connection)
    if existing is None:
        for name in ("schema.sql", "seed.sql", "accepted_paper_schedule.sql"):
            connection.exec_driver_sql((SQL_DIRECTORY / name).read_text(encoding="utf-8"))
        return "Created the original schema, deterministic seed, and schedule view."
    if existing[0] != OWNER_MARKER:
        raise ValueError("Refusing to modify a schema without the assignment ownership marker.")
    connection.exec_driver_sql((SQL_DIRECTORY / "accepted_paper_schedule.sql").read_text(encoding="utf-8"))
    check_schema(connection)
    return "Existing data preserved; schedule view installed."


def main():
    engine = environment_engine()
    try:
        with engine.begin() as connection:
            message = initialize_database(connection)
        print(message)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
