import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

from fizgig_ko.catalog import Catalog  # noqa: E402


def make():
    return Catalog(
        {
            "Start Training": "학습 시작",
            "Cancel": "취소",
            "Version {0}": "버전 {0}",
            "{0} images in {1}": "{1} 안에 이미지 {0}개",
            "Step {0}/{1}": "스텝 {0}/{1}",
            "same": "same",
            "empty": "",
        },
        log={"Training started.\n": "학습을 시작했습니다.\n",
             "[queue] removed {0}": "[큐] {0} 제거됨"},
    )


def test_exact():
    c = make()
    assert c.tr("Start Training") == "학습 시작"
    assert c.tr("Cancel") == "취소"


def test_unknown_passthrough_and_non_str():
    c = make()
    assert c.tr("Nope") == "Nope"
    assert c.tr(5) == 5
    assert c.tr(None) is None
    assert c.tr("") == ""


def test_whitespace_tolerant():
    c = make()
    assert c.tr("  Cancel\n") == "  취소\n"
    assert c.tr("Cancel ") == "취소 "


def test_template():
    c = make()
    assert c.tr("Version v4.2.0") == "버전 v4.2.0"
    assert c.tr("Version ") == "버전 "
    assert c.tr("12 images in D:\\x") == "D:\\x 안에 이미지 12개"
    assert c.tr("Step 3/10\n") == "스텝 3/10\n"


def test_template_multiline():
    c = Catalog({"Failed:\n{0}": "실패:\n{0}"})
    assert c.tr("Failed:\nline1\nline2") == "실패:\nline1\nline2"


def test_reverse():
    c = make()
    assert c.untr("학습 시작") == "Start Training"
    assert c.untr("취소\n") == "Cancel\n"
    assert c.untr("unknown") == "unknown"
    assert c.untr(3) == 3


def test_identity_and_empty_skipped():
    c = make()
    assert c.tr("same") == "same"
    assert c.tr("empty") == "empty"
    assert "same" not in c.reverse


def test_log_catalog():
    c = make()
    assert c.tr_log("Training started.\n") == "학습을 시작했습니다.\n"
    assert c.tr_log("[queue] removed foo") == "[큐] foo 제거됨"
    # falls back to the UI catalog
    assert c.tr_log("Cancel") == "취소"
    # UI catalog does not see log-only strings
    assert c.tr("Training started.\n") == "Training started.\n"


def test_cache_does_not_break_results():
    c = make()
    for _ in range(3):
        assert c.tr("Version 1") == "버전 1"
        assert c.tr("zzz") == "zzz"


def test_template_translates_captured_pieces():
    c = Catalog({"You're on {0}. {1}": "현재 {0} 사용 중입니다. {1}",
                 "Close the app to update.": "업데이트하려면 앱을 닫으세요.",
                 "Status: {0}": "상태: {0}", "Busy": "작업 중"})
    assert c.tr("You're on v1. Close the app to update.") == "현재 v1 사용 중입니다. 업데이트하려면 앱을 닫으세요."
    assert c.tr("Status: Busy") == "상태: 작업 중"
    assert c.tr("Status: 42") == "상태: 42"



def test_template_recursion_with_whitespace():
    c = Catalog({"Status: {0}": "상태: {0}", "Busy": "작업 중"})
    assert c.tr("Status: Busy" + chr(10)) == "상태: 작업 중" + chr(10)


def test_trailing_punctuation_fallback():
    c = Catalog({"Learning Rate": "학습률", "Browse": "찾아보기"})
    assert c.tr("Learning Rate:") == "학습률:"
    assert c.tr("Browse…") == "찾아보기…"
    assert c.tr("Browse...") == "찾아보기..."
    assert c.tr("Nope:") == "Nope:"


def test_segment_fallback():
    c = Catalog({"Base model for training.": "학습용 베이스 모델.", "Download": "다운로드",
                 "Step {0}": "스텝 {0}"})
    sep = "  ·  "
    assert c.tr("Base model for training." + sep + "~9.5GB fp8 (x.safetensors)") == \
        "학습용 베이스 모델." + sep + "~9.5GB fp8 (x.safetensors)"
    assert c.tr("Download\nStep 3") == "다운로드\n스텝 3"
    assert c.tr("foo\nbar") == "foo\nbar"


def test_wild_template_does_not_swallow_separators():
    c = Catalog({"{0} GB: {1}": "{0} GB: {1}", "up to {0} MP": "최대 {0} MP",
                 "Failed:\n{0}": "실패:\n{0}"})
    sep = "   ·   "
    assert c.tr("16 GB: up to 0.25 MP" + sep + "24 GB: up to 0.5 MP") == \
        "16 GB: 최대 0.25 MP" + sep + "24 GB: 최대 0.5 MP"
    # a template whose own text contains the separator may still capture across it
    assert c.tr("Failed:\nline1\nline2") == "실패:\nline1\nline2"



def test_leading_newline_key_matches_bare_segment():
    # a message assembled as msg += "\n\nDevice VRAM …" reaches the lookup one bare segment
    # at a time, so the entry has to fire without its own leading newlines
    c = Catalog({"Model unloaded.": "모델을 언로드했습니다.",
                 "\n\nDevice VRAM {0} / {1} GB": "\n\n장치 VRAM {0} / {1} GB"})
    assert c.tr("Model unloaded.\n\nDevice VRAM 2.1 / 24.0 GB") == \
        "모델을 언로드했습니다.\n\n장치 VRAM 2.1 / 24.0 GB"


def test_bare_segment_not_swallowed_by_other_template():
    c = Catalog({"Saved {0}": "저장됨: {0}",
                 "\n\nSaved natively — no conversion.": "\n\n그대로 저장했습니다 — 변환 없음."})
    assert c.tr("Done.\n\nSaved natively — no conversion.") == \
        "Done.\n\n그대로 저장했습니다 — 변환 없음."


def test_explicit_entry_beats_derived_bare_form():
    c = Catalog({"\n\nRetry.": "\n\n다시 시도하세요.", "Retry.": "재시도."})
    assert c.tr("Failed.\n\nRetry.") == "Failed.\n\n재시도."


def test_log_template_piece_falls_back_to_ui_catalog():
    # tr_log's contract — the log catalogue first, then the UI one — has to reach the pieces a
    # log template captures: a message assembled into a log line is a UI string
    c = Catalog({"Folder is missing.": "폴더가 없습니다."},
                {"[dataset] refused — {0}\n": "[dataset] 거부됨 — {0}\n"})
    assert c.tr_log("[dataset] refused — Folder is missing.\n") == "[dataset] 거부됨 — 폴더가 없습니다.\n"


def test_log_catalog_wins_over_ui_for_captured_pieces():
    c = Catalog({"Busy": "작업 중"}, {"Status: {0}\n": "상태: {0}\n", "Busy": "바쁨"})
    assert c.tr_log("Status: Busy\n") == "상태: 바쁨\n"
