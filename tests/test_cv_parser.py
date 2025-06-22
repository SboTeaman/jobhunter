from app import cv_parser


def test_build_profile_from_txt(sample_cv_bytes):
    p = cv_parser.build_profile("cv.txt", sample_cv_bytes)
    assert "Python" in p["skills"]
    assert "FastAPI" in p["skills"]
    assert p["years"] == 6
    assert p["seniority"] == 3  # senior
    assert p["language"] == "pl"


def test_detect_seniority_junior():
    data = "Junior Python Developer, 1 rok doświadczenia.".encode("utf-8")
    p = cv_parser.build_profile("cv.txt", data)
    assert p["seniority"] == 1


def test_years_filters_absurd_values():
    data = "Mam 200 lat i 4 lata doświadczenia w Java.".encode("utf-8")
    p = cv_parser.build_profile("cv.txt", data)
    assert p["years"] == 4


def test_empty_cv_has_no_skills():
    p = cv_parser.build_profile("cv.txt", b"   ")
    assert p["skills"] == []
