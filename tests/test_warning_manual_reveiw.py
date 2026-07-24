from src.validators import validate_government_warning


def test_incomplete_detected_warning_requires_manual_review():
    detected = (
        "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, "
        "WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY "
        "BECAUSE OF THE RISK OF BIRTH DEFECTS."
    )

    result = validate_government_warning(detected)

    assert result.status == "Manual Review"
    assert "could not verify the complete warning" in result.message


def test_missing_warning_still_requires_manual_review():
    result = validate_government_warning("")

    assert result.status == "Manual Review"

