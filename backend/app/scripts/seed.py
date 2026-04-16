from app.core.database import SessionLocal
from app.services.seed_service import SeedService


def main() -> None:
    db = SessionLocal()
    try:
        SeedService(db).ensure_seeded()
    finally:
        db.close()


if __name__ == "__main__":
    main()
