import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAW_DIR        = Path("data/raw")
DATASET_PATH   = RAW_DIR / "spotify_data.csv"
LOG_DIR        = Path("logs")
LOG_FILE       = LOG_DIR / "ingestion.log"
CHECKSUM_FILE  = LOG_DIR / "checksum.json"
KAGGLE_DATASET = "amitanshjoshi/spotify-1million-tracks"

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _setup_kaggle_credentials() -> None:
    kaggle_dir  = Path.home() / ".config" / "kaggle"
    kaggle_json = kaggle_dir / "kaggle.json"
    if kaggle_json.exists():
        return
    username = os.getenv("KAGGLE_USERNAME")
    key      = os.getenv("KAGGLE_KEY")
    if not username or not key:
        raise EnvironmentError(
            "KAGGLE_USERNAME and KAGGLE_KEY must be set in your .env file."
        )
    os.makedirs(kaggle_dir, exist_ok=True)
    kaggle_json.write_text(json.dumps({"username": username, "key": key}))
    kaggle_json.chmod(0o600)
    logger.info("Kaggle credentials written to %s", kaggle_json)


def _compute_checksum(filepath: Path) -> str:
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _load_saved_checksum() -> str | None:
    if CHECKSUM_FILE.exists():
        return json.loads(CHECKSUM_FILE.read_text()).get("checksum")
    return None


def _save_checksum(checksum: str) -> None:
    CHECKSUM_FILE.write_text(
        json.dumps({"checksum": checksum, "saved_at": datetime.now().isoformat()}, indent=2)
    )


def _create_folders() -> None:
    folders = [
        "data/raw", "data/processed", "logs", "ml/models",
        "ingestion", "processing", "storage", "orchestration", "serving",
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    logger.info("Folder structure verified.")


def ingest() -> Path:
    _create_folders()
    _setup_kaggle_credentials()

    import kaggle

    if DATASET_PATH.exists():
        current = _compute_checksum(DATASET_PATH)
        saved   = _load_saved_checksum()
        if current == saved:
            logger.info("Dataset already exists. Checksum: %s", current)
            print(f"✅ Dataset already up to date — {DATASET_PATH}")
            print(f"   Checksum : {current}")
            return DATASET_PATH
        print("⚠️  Checksum mismatch — re-downloading...")
    else:
        print(f"⏳ Downloading {KAGGLE_DATASET} ... (2-3 minutes)")
        logger.info("Starting download of %s", KAGGLE_DATASET)

    kaggle.api.authenticate()
    kaggle.api.dataset_download_files(
        KAGGLE_DATASET,
        path=str(RAW_DIR),
        unzip=True,
        quiet=False,
        force=True,
    )

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Download complete but {DATASET_PATH} not found."
        )

    checksum = _compute_checksum(DATASET_PATH)
    _save_checksum(checksum)
    size_mb = DATASET_PATH.stat().st_size / (1024 ** 2)
    logger.info("Download complete. Size: %.1f MB | Checksum: %s", size_mb, checksum)
    print(f"✅ Download complete — {size_mb:.1f} MB")
    print(f"   Path     : {DATASET_PATH}")
    print(f"   Checksum : {checksum}")
    return DATASET_PATH


if __name__ == "__main__":
    try:
        path = ingest()
        print(f"\n🎵 Ready for processing: {path}")
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        print(f"\n❌ Ingestion failed: {e}")
        raise SystemExit(1)