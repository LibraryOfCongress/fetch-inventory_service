"""Guard against reintroducing the verification dashboard N+1.

VerificationJobListOutput must NOT expose tray_count / item_count /
non_tray_item_count. Those map to VerificationJob hybrid properties whose
instance side lazy-loads every related Tray/Item/NonTrayItem row per job just
to count them — an N+1 that made the verification dashboard slow. The dashboard
does not use the counts, so the list schema deliberately omits them.
"""
import pytest

from app.schemas.verification_jobs import VerificationJobListOutput

COUNT_FIELDS = ("tray_count", "item_count", "non_tray_item_count")


@pytest.mark.parametrize("field", COUNT_FIELDS)
def test_list_output_omits_lazy_count_fields(field):
    assert field not in VerificationJobListOutput.model_fields, (
        f"{field} is back on VerificationJobListOutput; it lazy-loads related "
        "rows per job (N+1). Keep counts off the dashboard list schema."
    )
