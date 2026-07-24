from src.parsers import parse_label_text


def test_parse_basic_label():
    sample_text = """
    OLD TOM DISTILLERY
    DISTILLED SPIRITS
    BOURBON WHISKEY
    45% ALC./VOL.
    750 mL
    GOVERNMENT WARNING:
    According to the Surgeon General, women should not drink alcoholic beverages during pregnancy...
    """

    label = parse_label_text(sample_text)

    assert label.brand_name == "OLD TOM DISTILLERY"
    assert label.beverage_type == "Distilled Spirits"
    assert label.class_type == "BOURBON WHISKEY"
    assert label.abv == "45%"
    assert "750" in label.net_contents
    assert "government warning" in label.government_warning.lower()


def test_parse_wine_front_label():
    sample_text = """
    PINE RIDGE
    VINEYARDS
    RDS
    P. R .V
    PINE RIDGE
    EST. 1976
    NAPA VALLEY
    CABERNET SAUVIGNON
    VINTAGE 2023
    ALC. 15.5% BY VOL.
    """

    label = parse_label_text(sample_text)

    assert label.brand_name == "PINE RIDGE VINEYARDS"
    assert label.beverage_type == "Wine"
    assert label.class_type == "CABERNET SAUVIGNON"
    assert label.abv == "15.5%"
    assert label.net_contents == ""
    assert label.government_warning == ""


def test_parse_coors_light_beer_label():
    sample_text = """
    Coors
    LIGHT
    LIGHT BEER
    4% ALC. BY VOL.
    341 ml
    Adolph Coors Company, Golden, Colorado, U.S.A.
    TORONTO, BARRIE, WINNIPEG, REGINA, EDMONTON
    """

    label = parse_label_text(sample_text)

    assert label.brand_name == "Coors LIGHT"
    assert label.beverage_type == "Beer"
    assert label.class_type == "LIGHT BEER"
    assert label.abv == "4%"
    assert label.net_contents.lower() == "341 ml"


def test_brand_parser_ignores_legal_and_address_lines():
    sample_text = """
    SIERRA NEVADA
    PALE ALE
    5.6% ALC. BY VOL.
    12 FL OZ
    Sierra Nevada Brewing Company, Chico, California, U.S.A.
    """

    label = parse_label_text(sample_text)

    assert label.brand_name == "SIERRA NEVADA"
    assert label.beverage_type == "Beer"
    assert label.class_type == "PALE ALE"

