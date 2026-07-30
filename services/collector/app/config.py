import os


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    host = os.getenv("APP_DB_HOST", "postgres")
    port = os.getenv("APP_DB_PORT", "5432")
    database = os.getenv("APP_DB_NAME")
    user = os.getenv("APP_DB_USER")
    password = os.getenv("APP_DB_PASSWORD")

    missing = [
        name
        for name, value in {
            "APP_DB_NAME": database,
            "APP_DB_USER": user,
            "APP_DB_PASSWORD": password,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing required database variables: "
            + ", ".join(missing)
        )

    return (
        f"postgresql://"
        f"{user}:{password}@{host}:{port}/{database}"
    )