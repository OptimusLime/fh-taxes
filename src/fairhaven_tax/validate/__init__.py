"""Validation package — Phase-1 gates (gates.py) + Phase-2 checks (checks.py)."""
from fairhaven_tax.validate.gates import (
    GateResult,
    ValidationFailure,
    run_all_gates,
    validate_aggregate_assessed,
    validate_parcel_count,
    validate_sales_floor,
)
from fairhaven_tax.validate.checks import (
    run_phase2_gates,
    validate_cross_source_pin_alignment,
    validate_modiv_history_sale_assessment,
    validate_no_negative_assessments,
    validate_prc_required_features,
    validate_prc_row_count,
    validate_sales_row_count,
    validate_sales_year_range,
)

__all__ = [
    # Phase 1 (existing)
    "GateResult",
    "ValidationFailure",
    "run_all_gates",
    "validate_aggregate_assessed",
    "validate_parcel_count",
    "validate_sales_floor",
    # Phase 2 (new)
    "run_phase2_gates",
    "validate_cross_source_pin_alignment",
    "validate_modiv_history_sale_assessment",
    "validate_no_negative_assessments",
    "validate_prc_required_features",
    "validate_prc_row_count",
    "validate_sales_row_count",
    "validate_sales_year_range",
]
