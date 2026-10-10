"""Chronological partitions; test targets are never evaluated in Week 1."""

import pandas as pd

WINDOWS = {
    "train": ("2011-01-01", "2011-12-31"),
    "validation": ("2012-01-01", "2012-06-30"),
    "test": ("2012-07-01", "2012-12-31"),
}


def split_data(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sorted_frame = frame.sort_values(
        by=["dteday", "hr", "instant"], ascending=True
    ).reset_index(drop=True)

    partitions: dict[str, pd.DataFrame] = {}
    for name, (start_str, end_str) in WINDOWS.items():
        start = pd.Timestamp(start_str)
        end = pd.Timestamp(end_str)
        mask = (sorted_frame["dteday"] >= start) & (sorted_frame["dteday"] <= end)
        part = sorted_frame.loc[mask].reset_index(drop=True)
        if part.empty:
            raise ValueError(f"Partition {name} must be nonempty")
        partitions[name] = part

    total_partition_rows = sum(len(p) for p in partitions.values())
    if total_partition_rows != len(sorted_frame):
        raise ValueError(
            f"Split is not complete: {total_partition_rows} rows assigned out of {len(sorted_frame)}"
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
