from src.validators import validate_brand_name


def test_brand_single_character_ocr_error_requires_manual_review():
    result = validate_brand_name(
        expected="Coors Light",
        detected="Coois LIGHT",
    )

    assert result.status == "Manual Review"
    assert "OCR" in result.message


def test_brand_exact_normalized_value_still_matches():
    result = validate_brand_name(
        expected="Coors Light",
        detected="COORS-LIGHT",
    )

    assert result.status == "Match"


def test_brand_distinct_product_remains_mismatch():
    result = validate_brand_name(
        expected="Coors Light",
        detected="Miller Lite",
    )

    assert result.status == "Mismatch"


def test_brand_multiple_differences_remain_mismatch():
    result = validate_brand_name(
        expected="Coors Light",
        detected="Coois Lite",
    )

    assert result.status == "Mismatch"