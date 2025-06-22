from app.sources import justjoin


def test_parse_offer_html_extracts_fields(jj_html, jj_url):
    offer = justjoin.parse_offer_html(jj_html, jj_url)
    assert offer["company"] == "Reef Technologies"
    assert offer["location"] == "Warszawa"
    assert offer["remote"] is True
    assert "Python" in offer["skills"]
    assert "Docker" in offer["skills"]
    assert offer["source"] == "JustJoin.it"


def test_parse_prefers_pln_salary(jj_html, jj_url):
    offer = justjoin.parse_offer_html(jj_html, jj_url)
    # Powinien wybrać PLN, nie GBP, z jednostką godzinową.
    assert offer["salary"] == "180-280 PLN/h"


def test_title_strips_company_and_city(jj_html, jj_url):
    offer = justjoin.parse_offer_html(jj_html, jj_url)
    assert "Reef" not in offer["title"]
    assert "Warszawa" not in offer["title"]
    assert "Senior" in offer["title"]


def test_fallback_offer_from_slug_only():
    url = "https://justjoin.it/job-offer/acme-junior-java-developer-krakow"
    offer = justjoin._fallback_offer(url)
    assert offer["source"] == "JustJoin.it"
    assert offer["location"] == "Krakow"
    assert "Junior" in offer["title"]


def test_parse_missing_data_does_not_crash():
    offer = justjoin.parse_offer_html("<html>no data</html>",
                                      "https://justjoin.it/job-offer/x-dev-warszawa")
    assert offer["company"] == ""
    assert offer["skills"] == []
    assert offer["title"]  # tytuł ze sluga
