from src.models import OCRLine, OCRResult
from src.parsers import parse_label_text


def test_location_aware_brand_prefers_large_centered_text():
    ocr_result = OCRResult(
        text="\n".join(
            [
                "smoothness and character.",
                "Coors",
                "LIGHT",
                "LIGHT BEER",
                "4% ALC. BY VOL.",
                "341 ml",
            ]
        ),
        lines=[
            OCRLine(
                text="smoothness and character.",
                x=20,
                y=360,
                width=220,
                height=18,
            ),
            OCRLine(
                text="Coors",
                x=330,
                y=100,
                width=260,
                height=80,
            ),
            OCRLine(
                text="LIGHT",
                x=355,
                y=185,
                width=210,
                height=60,
            ),
            OCRLine(
                text="LIGHT BEER",
                x=370,
                y=260,
                width=180,
                height=24,
            ),
            OCRLine(
                text="4% ALC. BY VOL.",
                x=375,
                y=300,
                width=170,
                height=18,
            ),
            OCRLine(
                text="341 ml",
                x=410,
                y=330,
                width=90,
                height=18,
            ),
        ],
    )

    label = parse_label_text(ocr_result)

    assert label.brand_name == "Coors LIGHT"
    assert label.class_type == "LIGHT BEER"
    assert label.abv == "4%"
    assert "341" in label.net_contents


def test_location_aware_brand_does_not_join_distant_text():
    ocr_result = OCRResult(
        text="SIDE PANEL\nBRAND",
        lines=[
            OCRLine(
                text="SIDE PANEL",
                x=10,
                y=100,
                width=140,
                height=20,
            ),
            OCRLine(
                text="BRAND",
                x=400,
                y=100,
                width=240,
                height=70,
            ),
        ],
    )

    label = parse_label_text(ocr_result)

    assert label.brand_name == "BRAND"
