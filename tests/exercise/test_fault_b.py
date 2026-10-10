from pathlib import Path

import pandas as pd
import pytest

from bike_demand.validate import load_data

pytestmark = pytest.mark.exercise
FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_fault_b_rejects_non_integer_month(tmp_path):
    control_path = FIXTURES / "fault-b-valid-control.csv"
    fault_path = FIXTURES / "fault-b-noninteger-month.csv"
    control = pd.read_csv(control_path)
    fault = pd.read_csv(fault_path)

    # Both copies retain every column and differ in exactly one cell.
    assert fault.shape == control.shape
    assert list(fault.columns) == list(control.columns)
    differences = fault.ne(control)
    assert differences.to_numpy().sum() == 1
    assert differences.loc[0, "mnth"]
    assert fault.loc[0, "mnth"] == 1.5

    # The unchanged training-row control must be accepted first.
    control_before = control_path.read_bytes()
    validated = load_data(control_path)
    assert len(validated) == 2
    assert validated["dteday"].dt.year.eq(2011).all()
    assert control_path.read_bytes() == control_before

    # 1.5 is in range but not an integer; reject it without repairing the file.
    input_path = tmp_path / "fault-b.csv"
    input_path.write_bytes(fault_path.read_bytes())
    before = input_path.read_bytes()
    with pytest.raises(ValueError, match=r"\bmnth\b"):
        load_data(input_path)
    assert input_path.read_bytes() == before
