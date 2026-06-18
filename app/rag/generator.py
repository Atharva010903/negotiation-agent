"""
Generates ~50 synthetic procurement benchmark records and writes them to CSV.
Each record represents a historical negotiation outcome in a specific industry.
"""

import csv
import random
from pathlib import Path

from app.config import BENCHMARK_CSV, DATA_DIR

# Seed for reproducibility
random.seed(42)

INDUSTRIES = [
    "Information Technology",
    "Construction",
    "Healthcare",
    "Logistics",
    "Retail",
    "Manufacturing",
    "Energy",
    "Telecommunications",
    "Automotive",
    "Agriculture",
]

PAYMENT_TERMS = [
    "Net 30",
    "Net 45",
    "Net 60",
    "Net 90",
    "Advance 50%",
    "COD",
    "2/10 Net 30",
    "Net 15",
]

DELIVERY_PERIODS = [
    "7 days",
    "14 days",
    "21 days",
    "30 days",
    "45 days",
    "60 days",
    "90 days",
]

NEGOTIATED_OUTCOMES = [
    "Deal closed at agreed price",
    "Deal closed with minor concessions",
    "Deal closed after extended negotiation",
    "Deal closed with volume discount",
    "Deal closed with payment term adjustment",
    "No deal — price gap too large",
    "No deal — quality concerns",
    "Deal closed at midpoint",
]


def _generate_record(record_id: int) -> dict:
    """Generate a single synthetic procurement benchmark record."""
    industry = random.choice(INDUSTRIES)
    avg_discount = round(random.uniform(3.0, 25.0), 1)
    payment_term = random.choice(PAYMENT_TERMS)
    delivery_period = random.choice(DELIVERY_PERIODS)
    moq = random.choice([10, 25, 50, 100, 200, 500, 1000])
    contract_size = random.choice(
        [5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]
    )
    outcome = random.choice(NEGOTIATED_OUTCOMES)
    supplier_rating = round(random.uniform(2.5, 5.0), 1)

    return {
        "record_id": record_id,
        "industry": industry,
        "average_discount_pct": avg_discount,
        "payment_terms": payment_term,
        "delivery_period": delivery_period,
        "moq": moq,
        "contract_size_usd": contract_size,
        "negotiated_outcome": outcome,
        "supplier_rating": supplier_rating,
    }


def generate_benchmark_csv(
    output_path: Path | None = None, num_records: int = 50
) -> Path:
    """
    Create a CSV file containing synthetic procurement benchmark data.

    Parameters
    ----------
    output_path : Path, optional
        Where to write the CSV. Defaults to config.BENCHMARK_CSV.
    num_records : int
        Number of records to generate.

    Returns
    -------
    Path
        The path to the written CSV file.
    """
    output_path = output_path or BENCHMARK_CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = [_generate_record(i + 1) for i in range(num_records)]
    fieldnames = list(records[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"[RAG-Generator] Wrote {num_records} benchmark records to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_benchmark_csv()
