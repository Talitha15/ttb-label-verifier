from src.models import OCRLine, OCRResult
from src.parsers import parse_label_text


def test_abv_prefers_alcohol_context_over_marketing_percentage():
    result = OCRResult(
        text=(
            "SIERRA NEVADA\nPALE ALE\n100% family owned\n"
            "5.6%\nALC./VOL.\n12 FL. OZ."
        ),
        lines=[
            OCRLine(
                text="SIERRA NEVADA",
                x=300,
                y=100,
                width=300,
                height=70,
            ),
            OCRLine(
                text="PALE ALE",
                x=310,
                y=240,
                width=280,
                height=90,
            ),
            OCRLine(
                text="100% family owned",
                x=390,
                y=470,
                width=180,
                height=20,
            ),
            OCRLine(
                text="5.6%",
                x=220,
                y=510,
                width=60,
                height=24,
            ),
            OCRLine(
                text="ALC./VOL.",
                x=215,
                y=535,
                width=90,
                height=20,
            ),
            OCRLine(
                text="12 FL. OZ.",
                x=450,
                y=535,
                width=130,
                height=20,
            ),
        ],
    )

    label = parse_label_text(result)

    assert label.abv == "5.6%"


def test_abv_parses_not_less_not_more_range():
    text = (
        "BUDWEISER\n"
        "NOT LESS THAN 4.5% ALCOHOL BY VOLUME "
        "AND NOT MORE THAN 5% ALCOHOL BY VOLUME"
    )

    label = parse_label_text(text)

    assert label.abv == "4.5%-5%"
