from app.dedup import dedup_offers


def _o(id, source, title, company, **kw):
    base = {"id": id, "source": source, "title": title, "company": company,
            "location": "", "remote": False, "salary": "", "url": f"http://{source}/{id}",
            "skills": [], "description": ""}
    base.update(kw)
    return base


def test_merges_same_offer_from_two_portals():
    offers = [
        _o("1", "JustJoin.it", "Senior Python Developer", "Acme", skills=["Python"]),
        _o("2", "NoFluffJobs", "Senior Python Developer", "Acme", skills=["Python", "Docker"], salary="20000-25000 PLN"),
    ]
    result = dedup_offers(offers)
    assert len(result) == 1
    merged = result[0]
    assert set(merged["sources"]) == {"JustJoin.it", "NoFluffJobs"}
    assert merged["skills"] == ["Python", "Docker"]  # bogatszy zestaw
    assert merged["salary"] == "20000-25000 PLN"     # uzupełnione


def test_different_cities_same_role_merged():
    offers = [
        _o("1", "JustJoin.it", "Python Developer (Warszawa)", "Acme"),
        _o("2", "JustJoin.it", "Python Developer (Kraków)", "Acme"),
    ]
    assert len(dedup_offers(offers)) == 1


def test_distinct_offers_not_merged():
    offers = [
        _o("1", "X", "Python Developer", "Acme"),
        _o("2", "X", "Java Developer", "Acme"),
    ]
    assert len(dedup_offers(offers)) == 2


def test_offers_without_company_kept_separate():
    offers = [
        _o("1", "X", "Developer", ""),
        _o("2", "X", "Developer", ""),
    ]
    assert len(dedup_offers(offers)) == 2
