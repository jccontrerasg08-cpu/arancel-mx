"""Shared filesystem paths for the local comex layer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STATE_DIR = DATA_DIR / "state"
ALERTS_DIR = DATA_DIR / "alerts"
LEGAL_CORPUS_DIR = DATA_DIR / "legal_corpus"
DB_PATH = DATA_DIR / "comex.duckdb"
MANIFEST_PATH = DATA_DIR / "manifest.json"
CARTERA_PATH = DATA_DIR / "cartera.json"
ALERTS_PATH = ALERTS_DIR / "alerts.jsonl"


def ensure_data_dirs() -> None:
    """Create runtime data directories used by ETL and watchers."""
    for path in (DATA_DIR, RAW_DIR, STATE_DIR, ALERTS_DIR, LEGAL_CORPUS_DIR):
        path.mkdir(parents=True, exist_ok=True)
