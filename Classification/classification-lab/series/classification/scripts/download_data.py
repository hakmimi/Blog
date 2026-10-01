"""Download and validate the official UCI Bank Marketing archive."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

SOURCE_URL = "https://archive.ics.uci.edu/static/public/222/bank%2Bmarketing.zip"
EXPECTED_ROWS = 41_188
EXPECTED_COLUMNS = [
    "age", "job", "marital", "education", "default", "housing", "loan",
    "contact", "month", "day_of_week", "duration", "campaign", "pdays",
    "previous", "poutcome", "emp.var.rate", "cons.price.idx",
    "cons.conf.idx", "euribor3m", "nr.employed", "y",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_csv(archive_bytes: bytes) -> tuple[bytes, str]:
    """Find the full additional CSV, including inside a nested zip."""
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as outer:
        for name in outer.namelist():
            if name.replace("\\", "/").endswith("bank-additional-full.csv"):
                return outer.read(name), name
        for name in outer.namelist():
            if name.lower().endswith(".zip"):
                nested_bytes = outer.read(name)
                with zipfile.ZipFile(io.BytesIO(nested_bytes)) as nested:
                    for inner in nested.namelist():
                        if inner.replace("\\", "/").endswith("bank-additional-full.csv"):
                            return nested.read(inner), f"{name}!/{inner}"
    raise RuntimeError("bank-additional-full.csv was not found in the UCI archive")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    generated = root / "artifacts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)

    request = Request(SOURCE_URL, headers={"User-Agent": "classification-lab/1.0"})
    with urlopen(request, timeout=120) as response:
        archive = response.read()
    csv_bytes, member = find_csv(archive)
    destination = raw_dir / "bank-additional-full.csv"
    destination.write_bytes(csv_bytes)

    frame = pd.read_csv(destination, sep=";")
    problems: list[str] = []
    if len(frame) != EXPECTED_ROWS:
        problems.append(f"expected {EXPECTED_ROWS} rows, found {len(frame)}")
    if list(frame.columns) != EXPECTED_COLUMNS:
        problems.append(f"unexpected columns: {list(frame.columns)}")
    if set(frame["y"].unique()) != {"yes", "no"}:
        problems.append(f"unexpected targets: {sorted(frame['y'].unique())}")
    if problems:
        destination.unlink(missing_ok=True)
        raise ValueError("; ".join(problems))

    metadata = {
        "dataset": "UCI Bank Marketing",
        "dataset_page": "https://archive.ics.uci.edu/dataset/222/bank+marketing",
        "doi": "https://doi.org/10.24432/C5K306",
        "license": "CC BY 4.0",
        "creators": ["S. Moro", "P. Rita", "P. Cortez"],
        "source_url": SOURCE_URL,
        "archive_sha256": sha256(archive),
        "selected_member": member,
        "retrieved_file": destination.name,
        "csv_sha256": sha256(csv_bytes),
        "rows": len(frame),
        "input_features": len(frame.columns) - 1,
        "columns": list(frame.columns),
        "targets": sorted(frame["y"].unique().tolist()),
        "delimiter": ";",
    }
    (generated / "data_manifest.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
