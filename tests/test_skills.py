from app.skills import extract_skills


def test_extracts_common_technologies():
    found = extract_skills("Doświadczenie w Python, Django i PostgreSQL oraz Docker.")
    assert {"Python", "Django", "PostgreSQL", "Docker"} <= found


def test_word_boundaries_avoid_false_positives():
    # "go" w "google" nie powinno dać Go; "r" w "praca" nie powinno dać R.
    found = extract_skills("Pracujemy w google nad świetną pracą.")
    assert "Go" not in found
    assert "R" not in found


def test_handles_special_chars_csharp_cpp():
    found = extract_skills("Stack: C#, C++ oraz .NET.")
    assert "C#" in found
    assert "C++" in found


def test_empty_text_returns_empty_set():
    assert extract_skills("") == set()
    assert extract_skills(None) == set()


def test_aliases_map_to_canonical():
    assert "JavaScript" in extract_skills("znajomość JS i ES6")
    assert "Kubernetes" in extract_skills("wdrożenia na k8s")
