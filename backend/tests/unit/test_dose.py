from app.services.dose import administered_dose, compose_dose, parse_dose


def test_administered_dose_multiplies_unit_strength_by_quantity() -> None:
    assert administered_dose("1mg", 2) == "2mg"
    assert administered_dose("1.5 mg", 2) == "3mg"
    assert administered_dose("325mg", 1) == "325mg"


def test_compose_and_parse_dose_round_trip() -> None:
    assert compose_dose("1", "mg") == "1mg"
    amount, unit = parse_dose("5mg")
    assert amount == "5"
    assert unit == "mg"
