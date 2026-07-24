from src.parsers import parse_label_text


def test_high_abv_is_valid_when_alcohol_context_is_present():
    sample_text = """
    OLD TOM DISTILLERY
    DISTILLED SPIRITS
    BOURBON WHISKEY
    45% ALC./VOL.
    750 mL
    """

    label = parse_label_text(sample_text)

    assert label.abv == "45%"


def test_high_marketing_percentage_loses_to_contextual_abv():
    sample_text = """
    OLD TOM DISTILLERY
    DISTILLED SPIRITS
    BOURBON WHISKEY
    100% FAMILY OWNED
    45% ALC./VOL.
    750 mL
    """

    label = parse_label_text(sample_text)

    assert label.abv == "45%"
