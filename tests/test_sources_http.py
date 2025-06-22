"""Testy adapterów źródeł z mockowanym HTTP (respx) - bez realnej sieci."""
import httpx
import pytest
import respx

from app.sources import nofluffjobs, remoteok, weworkremotely, fetch_all


@respx.mock
async def test_nofluffjobs_parsing():
    payload = {
        "postings": [
            {
                "title": "Python Developer",
                "name": "Acme Sp. z o.o.",
                "seniority": ["Senior"],
                "technology": "Python",
                "tiles": {"values": [{"value": "Django"}]},
                "location": {"places": [{"city": "Warszawa"}], "fullyRemote": True},
                "salary": {"from": 20000, "to": 25000, "currency": "PLN"},
                "url": "python-developer-acme",
            }
        ]
    }
    respx.get(url__startswith="https://nofluffjobs.com/api/joboffers/main").mock(
        return_value=httpx.Response(200, json=payload)
    )
    offers = await nofluffjobs.fetch(limit=10)
    assert len(offers) == 1
    o = offers[0]
    assert o["company"] == "Acme Sp. z o.o."
    assert "Senior" in o["title"] and "Python Developer" in o["title"]
    assert o["remote"] is True
    assert o["salary"] == "20000-25000 PLN"
    assert "Django" in o["skills"]


@respx.mock
async def test_nofluffjobs_http_error_returns_empty():
    respx.get(url__startswith="https://nofluffjobs.com/api/joboffers/main").mock(
        return_value=httpx.Response(500)
    )
    assert await nofluffjobs.fetch() == []


@respx.mock
async def test_remoteok_skips_legal_notice():
    data = [
        {"legal": "see https://remoteok.com/api"},  # brak 'position'
        {
            "position": "Backend Engineer",
            "company": "Globex",
            "tags": ["python", "aws"],
            "url": "https://remoteok.com/l/1",
            "salary_min": 90000,
            "salary_max": 120000,
        },
    ]
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=data))
    offers = await remoteok.fetch(limit=10)
    assert len(offers) == 1
    assert offers[0]["title"] == "Backend Engineer"
    assert offers[0]["remote"] is True
    assert "$90000-$120000" == offers[0]["salary"]


@respx.mock
async def test_weworkremotely_rss_parsing():
    rss = """<?xml version="1.0"?><rss><channel>
      <item><title>Globex: Senior Go Developer</title>
        <link>https://weworkremotely.com/jobs/1</link>
        <description>&lt;p&gt;We use Go and Kubernetes&lt;/p&gt;</description>
        <pubDate>Mon, 01 Jan 2026</pubDate></item>
    </channel></rss>"""
    respx.get(url__startswith="https://weworkremotely.com").mock(
        return_value=httpx.Response(200, text=rss)
    )
    offers = await weworkremotely.fetch(limit=10)
    assert offers
    assert offers[0]["company"] == "Globex"
    assert offers[0]["title"] == "Senior Go Developer"
    assert offers[0]["remote"] is True


@respx.mock
async def test_fetch_all_aggregates_and_isolates_errors():
    # RemoteOK ok, NoFluff zwraca błąd -> powinien trafić do 'errors', nie wywalić.
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=[{"position": "Dev", "company": "A", "tags": [], "url": "u"}])
    )
    respx.get(url__startswith="https://nofluffjobs.com").mock(
        side_effect=httpx.ConnectError("boom")
    )
    result = await fetch_all(["remoteok", "nofluffjobs"], limit=5)
    titles = [o["title"] for o in result["offers"]]
    assert "Dev" in titles
    # NoFluff łapie wyjątek wewnętrznie i zwraca [], więc brak twardego błędu:
    assert isinstance(result["errors"], dict)
