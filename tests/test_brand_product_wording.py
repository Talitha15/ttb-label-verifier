from src.validators import validate_brand_name


def test_brand_with_product_descriptor_routes_to_manual_review():
    result = validate_brand_name(
        "Jim Beam",
        "JIM BEAM BOURBON",
    )

    assert result.status == "Manual Review"


def test_brand_with_reserve_line_routes_to_manual_review():
    result = validate_brand_name(
        "Kendall-Jackson",
        "KENDALL-JACKSON VINTNER'S RESERVE",
    )

    assert result.status == "Manual Review"


def test_minor_brand_spelling_difference_plus_product_line_is_manual():
    result = validate_brand_name(
        "Kendal-Jackson",
        "KENDALL-JACKSON VINTNER'S RESERVE",
    )

    assert result.status == "Manual Review"


def test_brand_with_expression_wording_routes_to_manual_review():
    result = validate_brand_name(
        "Meiomi",
        "MEIOMI THE BRUCE EXPRESSION",
    )

    assert result.status == "Manual Review"


def test_unrelated_brand_text_remains_mismatch():
    result = validate_brand_name(
        "Jack Daniels",
        "EVERY DR MADE IN",
    )

    assert result.status == "Mismatch"


def test_exact_brand_still_matches():
    result = validate_brand_name(
        "Captain Morgan",
        "CAPTAIN MORGAN",
    )

    assert result.status == "Match"
