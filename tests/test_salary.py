from app.salary import to_monthly_pln


def test_monthly_pln_no_unit():
    assert to_monthly_pln("18000-25000 PLN") == 18000


def test_hourly_pln_converted_to_month():
    # 180 PLN/h * 168h = 30240
    assert to_monthly_pln("180-280 PLN/h") == 180 * 168


def test_foreign_currency_converted():
    # 5000-7000 EUR/mc * 4.3 ~ 21500
    val = to_monthly_pln("5000-7000 EUR/mc")
    assert val == round(5000 * 4.3)


def test_unparseable_returns_none():
    assert to_monthly_pln("") is None
    assert to_monthly_pln("konkurencyjne") is None
    assert to_monthly_pln("100 USD") is None  # brak zakresu od-do


def test_handles_spaces_in_numbers():
    assert to_monthly_pln("20 000-30 000 PLN") == 20000
