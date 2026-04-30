import logging
from pathlib import Path
from datetime import timedelta

from prefect import flow, task
from prefect.tasks import task_input_hash
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@task(
    name="ingest_data",
    retries=3,
    retry_delay_seconds=10,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
)
def task_ingest() -> str:
    from ingestion.ingest import ingest
    return str(ingest())


@task(name="validate_raw", retries=2, retry_delay_seconds=5)
def task_validate_raw(csv_path: str) -> dict:
    from processing.validate import validate_raw
    return validate_raw(Path(csv_path))


@task(name="clean_data", retries=2, retry_delay_seconds=10)
def task_clean() -> str:
    from processing.clean import clean
    clean()
    return "data/processed/spotify_clean"


@task(name="load_analytics", retries=3, retry_delay_seconds=10)
def task_load(processed_path: str) -> bool:
    from storage.load import load
    load()
    return True


@task(name="train_ml", retries=1, retry_delay_seconds=30)
def task_train() -> str:
    from ml.train import train
    train()
    return "ml/models/boporflop_model"


@flow(
    name="spotilytics_pipeline",
    description="End-to-end Spotilytics data engineering pipeline — Group 6",
    log_prints=True,
)
def spotilytics_pipeline():
    print("=" * 52)
    print("  Spotilytics Pipeline — AI-620 Group 6")
    print("=" * 52)

    csv_path = task_ingest()
    print(f"\n✅ Step 1 — Ingestion done: {csv_path}")

    raw_report = task_validate_raw(csv_path)
    print(f"\n✅ Step 2 — Raw validation: {raw_report['passed']}/{raw_report['total']} passed")

    processed_path = task_clean()
    print(f"\n✅ Step 3 — Cleaning done: {processed_path}")

    task_load(processed_path)
    print("\n✅ Step 4 — Analytics loaded into PostgreSQL")

    model_path = task_train()
    print(f"\n✅ Step 5 — ML model trained: {model_path}")

    print("\n" + "=" * 52)
    print("  Pipeline complete!")
    print("=" * 52)


if __name__ == "__main__":
    spotilytics_pipeline()