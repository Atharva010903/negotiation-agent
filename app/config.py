"""
Centralised configuration for the Negotiation Agent platform.
Loads values from environment variables (.env) with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
CHROMA_DIR: Path = BASE_DIR / "chroma_db"
LOGS_DIR: Path = BASE_DIR / "logs"
DB_PATH: Path = BASE_DIR / "logs" / "negotiation.db"

# Ensure directories exist
for _d in (DATA_DIR, CHROMA_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Groq API ──────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── LLM Model Names ──────────────────────────────────────────────
BUYER_MODEL: str = os.getenv("BUYER_MODEL", "qwen/qwen3-32b")
SELLER_MODEL: str = os.getenv("SELLER_MODEL", "qwen/qwen3-32b")
MEDIATOR_MODEL: str = os.getenv("MEDIATOR_MODEL", "llama-3.1-8b-instant")

# ── RAG ───────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
CHROMA_COLLECTION: str = "procurement_benchmarks"
BENCHMARK_CSV: Path = DATA_DIR / "procurement_benchmarks.csv"

# ── Negotiation Defaults ─────────────────────────────────────────
MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "10"))
CONVERGENCE_THRESHOLD_PCT: float = float(
    os.getenv("CONVERGENCE_THRESHOLD_PCT", "2.0")
)

# ── LLM Temperature ──────────────────────────────────────────────
BUYER_TEMPERATURE: float = float(os.getenv("BUYER_TEMPERATURE", "0.6"))
SELLER_TEMPERATURE: float = float(os.getenv("SELLER_TEMPERATURE", "0.5"))
MEDIATOR_TEMPERATURE: float = float(os.getenv("MEDIATOR_TEMPERATURE", "0.1"))
