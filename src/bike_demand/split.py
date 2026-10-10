"""Chronological partitions; test targets are never evaluated in Week 1."""

import pandas as pd

WINDOWS = {
    "train": ("2011-01-01", "2011-12-31"),
    "validation": ("2012-01-01", "2012-06-30"),
    "test": ("2012-07-01", "2012-12-31"),
}


def split_data(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    partitions = {}
    for name, (start, end) in WINDOWS.items():
        mask = (frame["dteday"] >= pd.to_datetime(start)) & (
            frame["dteday"] <= pd.to_datetime(end)
        )
        part = frame.loc[mask].sort_values(["dteday", "hr", "instant"])
        if part.empty:
            raise ValueError(f"Partition {name} must be nonempty")
        partitions[name] = part

    total = sum(len(part) for part in partitions.values())
    if total != len(frame):
        raise ValueError(
            f"Partitions are not complete: {total} rows in partitions "
            f"but {len(frame)} rows in the input"
        )
    return partitions


def partition_summary(partitions: dict[str, pd.DataFrame]) -> dict:
    return {
        name: {
            "rows": len(part),
            "date_min": str(part["dteday"].min().date()),
            "date_max": str(part["dteday"].max().date()),
        }
        for name, part in partitions.items()
    }
