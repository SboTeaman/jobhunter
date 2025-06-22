from app.filters import apply_filters


def _o(**kw):
    base = {"id": "1", "title": "Dev", "company": "", "location": "", "remote": False,
            "salary": "", "url": "", "skills": [], "description": ""}
    base.update(kw)
    return base


def test_remote_only():
    offers = [_o(id="a", remote=True), _o(id="b", remote=False)]
    out = apply_filters(offers, remote_only=True)
    assert [o["id"] for o in out] == ["a"]


def test_location_substring():
    offers = [_o(id="a", location="Warszawa"), _o(id="b", location="Kraków")]
    out = apply_filters(offers, location="warsz")
    assert [o["id"] for o in out] == ["a"]


def test_salary_min_excludes_low():
    offers = [
        _o(id="a", salary="25000-30000 PLN"),
        _o(id="b", salary="8000-10000 PLN"),
    ]
    out = apply_filters(offers, salary_min=15000)
    assert [o["id"] for o in out] == ["a"]


def test_salary_min_keeps_unparseable():
    # Brak danych o widełkach != za mało - oferta zostaje.
    offers = [_o(id="a", salary=""), _o(id="b", salary="konkurencyjne")]
    out = apply_filters(offers, salary_min=15000)
    assert len(out) == 2


def test_no_filters_returns_all():
    offers = [_o(id="a"), _o(id="b")]
    assert len(apply_filters(offers)) == 2
