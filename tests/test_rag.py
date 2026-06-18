"""
Tests for the RAG pipeline — CSV generation, embedding, and retrieval.
"""

import os
from pathlib import Path

import pytest

from app.config import DATA_DIR


class TestBenchmarkCSVGeneration:
    """Tests for the synthetic CSV generator."""

    def test_generate_csv_creates_file(self, tmp_path):
        from app.rag.generator import generate_benchmark_csv

        output = tmp_path / "test_benchmarks.csv"
        result = generate_benchmark_csv(output_path=output, num_records=10)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_csv_has_correct_columns(self, tmp_path):
        import csv

        from app.rag.generator import generate_benchmark_csv

        output = tmp_path / "test_benchmarks.csv"
        generate_benchmark_csv(output_path=output, num_records=5)

        with open(output, "r") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        expected_columns = {
            "record_id",
            "industry",
            "average_discount_pct",
            "payment_terms",
            "delivery_period",
            "moq",
            "contract_size_usd",
            "negotiated_outcome",
            "supplier_rating",
        }
        assert set(row.keys()) == expected_columns

    def test_csv_has_correct_row_count(self, tmp_path):
        import csv

        from app.rag.generator import generate_benchmark_csv

        output = tmp_path / "test_benchmarks.csv"
        generate_benchmark_csv(output_path=output, num_records=50)

        with open(output, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # 50 data rows + 1 header row
        assert len(rows) == 51

    def test_csv_supplier_rating_range(self, tmp_path):
        import csv

        from app.rag.generator import generate_benchmark_csv

        output = tmp_path / "test_benchmarks.csv"
        generate_benchmark_csv(output_path=output, num_records=50)

        with open(output, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rating = float(row["supplier_rating"])
                assert 2.5 <= rating <= 5.0
