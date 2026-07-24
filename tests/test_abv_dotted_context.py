from src.parsers import parse_label_text


def test_abv_with_dotted_alc_vol_context():
    sample_text = """
    OLD TOM DISTILLERY
    DISTILLED SPIRITS
    BOURBON WHISKEY
    45% ALC./VOL.
    750 mL
    """

    label = parse_label_text(sample_text)

    assert label.abv == "45%"
