import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def engine():
    # Refuse unrelated databases for all mutation commands.
    database = os.environ.get("POSTGRES_DB", "arcadia_games")
    if database != "arcadia_games":
        raise ValueError("This project only operates on the arcadia_games database")
    url = URL.create("postgresql+psycopg", username=os.environ.get("POSTGRES_USER", "arcadia"),
                     password=os.environ["POSTGRES_PASSWORD"], host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
                     port=int(os.environ.get("POSTGRES_PORT", "5434")), database=database)
    return create_engine(url, connect_args={"options": "-c timezone=UTC -c search_path=arcadia,public"})
