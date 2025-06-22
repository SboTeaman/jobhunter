"""Testy app/scraper.py — bez rzeczywistych połączeń HTTP (respx mock)."""
import json
import pytest
import respx
import httpx

from app import scraper
from app.sources import justjoin


JJ_HTML_SINGLE = (
    r'<script>self.__next_f.push([1,"...'
    r'\"companyName\":\"Acme\",\"companyUrl\":\"https://x\",'
    r'\"body\":\"$46\",\"city\":\"Krakow\",'
    r'\"workplaceType\":{\"label\":\"remote\",\"value\":\"remote\"},'
    r'\"requiredSkills\":[{\"id\":\"Python\",\"name\":\"Python\",\"level\":4},'
    r'{\"id\":\"Docker\",\"name\":\"Docker\",\"level\":3}],'
    r'\"employmentTypes\":[{\"currency\":\"PLN\",\"from\":15000,\"fromPln\":null,'
    r'\"to\":20000,\"toPln\":null,\"type\":\"b2b\",\"unit\":\"month\"}]..."])</script>'
)

GENERIC_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"JobPosting","title":"DevOps Engineer","hiringOrganization":{"name":"TechCorp"},
"jobLocation":{"address":{"addressLocality":"Remote"}},"baseSalary":{"value":{"value":"8000-10000 PLN"}}}
</script>
</head><body><h1>DevOps Engineer</h1></body></html>
"""

NF_HTML = json.dumps({
    "props": {"pageProps": {"posting": {
        "title": "Backend Dev",
        "name": "TestCo",
        "specs": [{"requirements": {"values": [{"value": "Python"}]}}],
        "salary": {"from": 10000, "to": 15000, "currency": "PLN"},
    }}}
})
NF_HTML_FULL = f'<script id="__NEXT_DATA__" type="application/json">{NF_HTML}</script>'


@pytest.mark.asyncio
async def test_offer_from_url_justjoin():
    url = "https://justjoin.it/job-offer/acme-python-dev-krakow"
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, text=JJ_HTML_SINGLE))
        offer = await scraper.offer_from_url(url)
    assert offer["title"] != ""
    assert "Python" in offer["skills"]
    assert offer["remote"] is True


@pytest.mark.asyncio
async def test_offer_from_url_generic_jsonld():
    url = "https://example.com/jobs/devops"
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, text=GENERIC_HTML))
        offer = await scraper.offer_from_url(url)
    assert "DevOps" in offer["title"] or "devops" in offer["title"].lower()


@pytest.mark.asyncio
async def test_offer_from_url_http_error():
    url = "https://example.com/jobs/gone"
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(404))
        with pytest.raises(ValueError, match="HTTP 404"):
            await scraper.offer_from_url(url)


@pytest.mark.asyncio
async def test_offer_from_url_nofluffjobs():
    url = "https://nofluffjobs.com/pl/job/backend-dev"
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, text=NF_HTML_FULL))
        offer = await scraper.offer_from_url(url)
    assert offer["title"] != ""


def test_domain_extractor():
    assert scraper._domain("https://justjoin.it/job/x") == "justjoin.it"
    assert scraper._domain("https://nofluffjobs.com/job/y") == "nofluffjobs.com"
    assert scraper._domain("not-a-url") == ""
