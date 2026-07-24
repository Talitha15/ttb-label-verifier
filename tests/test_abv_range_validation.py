from src.validators import validate_abv


def test_exact_abv_matches_exact_abv():
    result = validate_abv("5.6", "5.6%")

    assert result.status == "Match"


def test_identical_abv_ranges_match():
    result = validate_abv("4.5-5", "4.5%-5%")

    assert result.status == "Match"


def test_expected_range_detected_boundary_requires_manual_review():
    result = validate_abv("4.5%-5%", "5%")

    assert result.status == "Manual Review"
    assert "one range boundary" in result.message


def test_expected_exact_detected_range_requires_manual_review():
    result = validate_abv("5%", "4.5%-5%")

    assert result.status == "Manual Review"


def test_disjoint_abv_values_mismatch():
    result = validate_abv("5.6%", "100%")

    assert result.status == "Mismatch"


def test_overlapping_nonidentical_ranges_require_manual_review():
    result = validate_abv("4.5%-5%", "4.8%-5.2%")

    assert result.status == "Manual Review"
