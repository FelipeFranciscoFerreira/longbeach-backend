import os
import sys
import time
import subprocess
import psycopg2
from app.core.config import settings

def wait_for_postgres():
    print("Waiting for PostgreSQL to be ready...")
    max_retries = 30
    retry_interval = 2
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                dbname=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
            )
            conn.close()
            print("PostgreSQL is ready!")
            return
        except psycopg2.OperationalError as e:
            print(f"[{attempt}/{max_retries}] PostgreSQL not ready yet ({e}). Retrying in {retry_interval}s...")
            time.sleep(retry_interval)
    print("Could not connect to PostgreSQL within the time limit. Exiting.")
    sys.exit(1)

def run_migrations():
    print("Running Alembic migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"])
    if result.returncode != 0:
        print("Failed to run Alembic migrations!")
        sys.exit(result.returncode)
    print("Migrations applied successfully!")

def start_server():
    print(f"Starting Uvicorn server for {settings.PROJECT_NAME}...")
    subprocess.run([
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

if __name__ == "__main__":
    wait_for_postgres()
    run_migrations()
    start_server()
