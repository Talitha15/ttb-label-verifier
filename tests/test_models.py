from src.models import LabelData


def test_label_data_defaults():
    label = LabelData()

    assert label.beverage_type == ""
    assert label.brand_name == ""
    assert label.class_type == ""
    assert label.abv == ""
    assert label.net_contents == ""
    assert label.government_warning == ""