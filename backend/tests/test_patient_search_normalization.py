from backend.utils.patient_search_normalization import (
    classify_patient_search_query,
    normalize_digits,
    normalize_egypt_phone,
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)


def test_arabic_name_normalization_handles_common_egyptian_variants():
    assert normalize_patient_name_for_search("أحمد") == "احمد"
    assert normalize_patient_name_for_search("إسلام") == "اسلام"
    assert normalize_patient_name_for_search("آمال") == "امال"
    assert normalize_patient_name_for_search("مصطفى") == "مصطفي"


def test_arabic_name_normalization_removes_diacritics_tatweel_and_noise():
    assert normalize_patient_name_for_search("  عَبْــد   الرَّحْمَن ") == "عبد الرحمن"


def test_digit_normalization_supports_arabic_and_persian_digits():
    assert normalize_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"
    assert normalize_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"


def test_egypt_phone_formats_share_one_canonical_value():
    expected = "+201012345678"
    assert normalize_egypt_phone("01012345678") == expected
    assert normalize_egypt_phone("+20 10 1234 5678") == expected
    assert normalize_egypt_phone("0020-10-1234-5678") == expected
    assert normalize_egypt_phone("٠١٠١٢٣٤٥٦٧٨") == expected


def test_phone_blind_index_is_deterministic_and_not_plaintext(monkeypatch):
    monkeypatch.setenv("PATIENT_SEARCH_HMAC_KEY", "patient-search-test-key-with-enough-randomness")
    local_hash = patient_phone_search_hash("01012345678")
    international_hash = patient_phone_search_hash("+201012345678")
    different_hash = patient_phone_search_hash("01112345678")
    assert local_hash == international_hash
    assert local_hash != different_hash
    assert "01012345678" not in local_hash
    assert len(local_hash) == 64


def test_query_classifier_distinguishes_file_phone_and_name():
    assert classify_patient_search_query("#1842") == "file_number"
    assert classify_patient_search_query("1842") == "file_number"
    assert classify_patient_search_query("01012345678") == "phone"
    assert classify_patient_search_query("+201012345678") == "phone"
    assert classify_patient_search_query("أحمد محمد") == "name"
