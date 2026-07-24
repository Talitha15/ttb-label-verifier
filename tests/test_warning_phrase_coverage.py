from src.validators import validate_government_warning


def test_reordered_bud_light_warning_is_substantially_complete():
    detected = (
        "ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK "
        "ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR "
        "OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS. BEVERAGES "
        "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. "
        "(2) CONSUMPTION OF ALCOHOLIC Sam's Man Cave"
    )

    result = validate_government_warning(detected)

    assert result.status == "Manual Review"
    assert "6 of 7" in result.message
    assert "substantially complete" in result.message


def test_complete_warning_out_of_order_is_substantially_complete():
    detected = (
        "CONSUMPTION OF ALCOHOLIC BEVERAGES MAY CAUSE HEALTH PROBLEMS "
        "ACCORDING TO THE SURGEON GENERAL RISK OF BIRTH DEFECTS "
        "IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY "
        "DURING PREGNANCY WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES"
    )

    result = validate_government_warning(detected)

    assert result.status == "Manual Review"
    assert "7 of 7" in result.message
    assert "reading order" in result.message


def test_partial_warning_reports_phrase_coverage():
    detected = (
        "ACCORDING TO THE SURGEON GENERAL WOMEN SHOULD NOT DRINK "
        "ALCOHOLIC BEVERAGES"
    )

    result = validate_government_warning(detected)

    assert result.status == "Manual Review"
    assert "2 of 7" in result.message
    assert "could not verify the complete warning" in result.message


def test_unrelated_text_does_not_look_complete():
    result = validate_government_warning(
        "Sam's Man Cave brewed with quality ingredients"
    )

    assert result.status == "Manual Review"
    assert "0 of 7" in result.message