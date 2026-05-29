from app.db.database import DATABASE_PATH, init_db


def main() -> None:
    init_db()
    print(f"Initialized database at {DATABASE_PATH}")


if __name__ == "__main__":
    main()
