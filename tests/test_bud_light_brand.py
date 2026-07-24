from src.models import OCRLine, OCRResult
from src.parsers import parse_label_text


def test_large_centered_bud_light_pair_beats_side_genuine():
    result = OCRResult(
        text="\n".join(
            [
                "GENUINE",
                "BUD",
                "LIGHT",
                "GENUINE",
                "LIGHT BEER",
                "12 FL. OZ.",
            ]
        ),
        lines=[
            OCRLine(
                text="GENUINE",
                x=80,
                y=160,
                width=55,
                height=72,
            ),
            OCRLine(
                text="BUD",
                x=340,
                y=150,
                width=250,
                height=105,
            ),
            OCRLine(
                text="LIGHT",
                x=315,
                y=250,
                width=300,
                height=105,
            ),
            OCRLine(
                text="GENUINE",
                x=820,
                y=160,
                width=55,
                height=72,
            ),
            OCRLine(
                text="LIGHT BEER",
                x=390,
                y=370,
                width=160,
                height=26,
            ),
            OCRLine(
                text="12 FL. OZ.",
                x=410,
                y=420,
                width=125,
                height=22,
            ),
        ],
    )

    label = parse_label_text(result)

    assert label.brand_name == "BUD LIGHT"
    assert label.class_type == "LIGHT BEER"
    assert label.net_contents == "12 FL. OZ"

