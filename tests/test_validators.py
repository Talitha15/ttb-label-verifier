from src.models import LabelData
from src.validators import (
    GOVERNMENT_WARNING_REQUIRED,
    validate_label,
)


def test_matching_label_values():
    expected = LabelData(
        beverage_type="Wine",
        brand_name="Pine Ridge Vineyards",
        class_type="Cabernet Sauvignon",
        abv="15.5%",
        net_contents="750 mL",
    )

    detected = LabelData(
        beverage_type="Wine",
        brand_name="PINE RIDGE VINEYARDS",
        class_type="CABERNET SAUVIGNON",
        abv="ALC. 15.5% BY VOL.",
        net_contents="750 ML",
        government_warning=GOVERNMENT_WARNING_REQUIRED,
    )

    result = validate_label(expected, detected)

    assert result.fields["beverage_type"].status == "Match"
    assert result.fields["brand_name"].status == "Match"
    assert result.fields["class_type"].status == "Match"
    assert result.fields["abv"].status == "Match"
    assert result.fields["net_contents"].status == "Match"
    assert result.fields["government_warning"].status == "Manual Review"
    assert result.overall_status == "Manual Review"


def test_missing_ocr_fields_require_manual_review():
    expected = LabelData(
        beverage_type="Wine",
        brand_name="Pine Ridge Vineyards",
        class_type="Cabernet Sauvignon",
        abv="15.5%",
        net_contents="750 mL",
    )

    detected = LabelData(
        beverage_type="Wine",
        brand_name="Pine Ridge Vineyards",
        class_type="Cabernet Sauvignon",
        abv="15.5%",
    )

    result = validate_label(expected, detected)

    assert result.fields["net_contents"].status == "Manual Review"
    assert result.fields["government_warning"].status == "Manual Review"
    assert result.overall_status == "Manual Review"


def test_mismatched_abv_causes_overall_mismatch():
    expected = LabelData(
        beverage_type="Wine",
        brand_name="Pine Ridge Vineyards",
        class_type="Cabernet Sauvignon",
        abv="15.5%",
        net_contents="750 mL",
    )

    detected = LabelData(
        beverage_type="Wine",
        brand_name="Pine Ridge Vineyards",
        class_type="Cabernet Sauvignon",
        abv="12.5%",
        net_contents="750 mL",
    )

    result = validate_label(expected, detected)

    assert result.fields["abv"].status == "Mismatch"
    assert result.overall_status == "Mismatch"


def test_abv_matches_without_percent_sign():
    expected = LabelData(
        abv="15.5",
    )

    detected = LabelData(
        abv="15.5%",
    )

    result = validate_label(expected, detected)

    assert result.fields["abv"].status == "Match"


def test_unitless_net_contents_matches_detected_ml():
    expected = LabelData(
        net_contents="341",
    )

    detected = LabelData(
        net_contents="341 ml",
    )

    result = validate_label(expected, detected)

    assert result.fields["net_contents"].status == "Match"


def test_net_contents_conflicting_units_mismatch():
    expected = LabelData(
        net_contents="341 ml",
    )

    detected = LabelData(
        net_contents="341 fl oz",
    )

    result = validate_label(expected, detected)

    assert result.fields["net_contents"].status == "Mismatch"


def test_partial_brand_name_requires_manual_review():
    expected = LabelData(
        brand_name="Coors",
    )

    detected = LabelData(
        brand_name="Coors Light",
    )

    result = validate_label(expected, detected)

    assert result.fields["brand_name"].status == "Manual Review"


def test_complete_brand_name_matches():
    expected = LabelData(
        brand_name="Coors Light",
    )

    detected = LabelData(
        brand_name="COORS-LIGHT",
    )

    result = validate_label(expected, detected)

    assert result.fields["brand_name"].status == "Match"


def test_broader_class_type_requires_manual_review():
    expected = LabelData(
        class_type="Beer",
    )

    detected = LabelData(
        class_type="Light Beer",
    )

    result = validate_label(expected, detected)

    assert result.fields["class_type"].status == "Manual Review"


def test_light_beer_exact_class_type_matches():
    expected = LabelData(
        class_type="Light Beer",
    )

    detected = LabelData(
        class_type="LIGHT BEER",
    )

    result = validate_label(expected, detected)

    assert result.fields["class_type"].status == "Match"
