from src.parsers import parse_label_text


def test_abv_context_accepts_common_alc_vol_separators():
    samples = (
        "45% ALC./VOL.",
        "45% ALC/VOL",
        "45% ALC-VOL",
        "45% ALCOHOL BY VOLUME",
        "45% ABV",
    )

    for sample in samples:
        label = parse_label_text(
            "OLD TOM DISTILLERY\n"
            "DISTILLED SPIRITS\n"
            "BOURBON WHISKEY\n"
            f"{sample}\n"
            "750 mL"
        )

        assert label.abv == "45%", sample
