"""web_ko.js (브라우저용 번역 엔진)가 catalog.py 와 같은 결과를 내는지 대조한다.

node 가 없으면 건너뜁니다(순수 파이썬 기여자 환경). 두 구현은 같은 규칙을 가져야 하므로 한쪽만 고치면 여기서 걸립니다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

from fizgig_ko.catalog import Catalog  # noqa: E402

JS = os.path.join(ROOT, "lib", "fizgig_ko", "web_ko.js")

_RUNNER = r"""
const fs = require("fs");
const [catPath, probePath, jsPath] = process.argv.slice(2);
globalThis.__KO_CAT = {m: JSON.parse(fs.readFileSync(catPath, "utf8"))};
require(jsPath);
const probes = JSON.parse(fs.readFileSync(probePath, "utf8"));
process.stdout.write(JSON.stringify(probes.map((s) => globalThis.__ko.tr(s))));
"""

_FILL = ["X", "12", "foo · bar", "a\nb", "", "7.5 GB", "🎲 Random", "…"]


def _probes(mapping):
    out = set()
    for en in mapping:
        out.add(en)
        out.add("  " + en + "\n")
        out.add(en.strip() + ":")
        out.add(en.strip() + "…")
        out.add("Zzz · " + en.strip() + " · Yyy")
        out.add("Line one\n" + en.strip() + "\nLine three")
        if re.search(r"\{\d+\}", en):
            for fill in _FILL:
                out.add(re.sub(r"\{\d+\}", fill, en))
            out.add(re.sub(r"\{\d+\}", "A", en, count=1))
    out.update(["", " ", "plain text nobody translated", "(5 images)", "x4 speed", "#7: abc", "🎲 Random",
                "Up 3 done", "Isabc"])
    return sorted(out)


def _run_js(mapping, probes):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, data in (("cat.json", mapping), ("probes.json", probes)):
            p = os.path.join(d, name)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            paths.append(p)
        runner = os.path.join(d, "run.js")
        with open(runner, "w", encoding="utf-8") as f:
            f.write(_RUNNER)
        r = subprocess.run(["node", runner, *paths, JS], capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)


def _compare(mapping, label):
    probes = _probes(mapping)
    cat = Catalog(mapping)
    want = [cat.tr(s) for s in probes]
    got = _run_js(mapping, probes)
    bad = [(s, w, g) for s, w, g in zip(probes, want, got) if w != g]
    assert not bad, f"{label}: {len(bad)} of {len(probes)} differ, e.g. {bad[:3]!r}"


def test_js_matches_python_on_a_synthetic_catalog():
    if not shutil.which("node"):
        return
    _compare({
        "Start Training": "학습 시작", "Cancel": "취소", "Version {0}": "버전 {0}",
        "{0} images in {1}": "{1} 안에 이미지 {0}개", "Step {0}/{1}": "스텝 {0}/{1}",
        "({0} images)": "(이미지 {0}장)", "x{0} speed": "{0}배속", "#{0}: {1}": "#{0}번: {1}",
        "Is{0}": "{0}임", "Up {0} done": "위 {0} 완료", "{0} GB: {1}": "{0} GB: {1}",
        "\n\nDevice VRAM {0} / {1} GB": "\n\n장치 VRAM {0} / {1} GB", "Saved {0}": "저장됨: {0}",
        "{0}{0} twice": "두 번 {0}", "🎲 Random": "🎲 무작위", "🎲{0}": "🎲 {0}", "Retry.": "재시도.",
        "Learning Rate:": "학습률:", "Browse…": "찾아보기…", "{0}": "{0}",
    }, "synthetic")


def test_js_matches_python_on_the_shipped_catalogs():
    if not shutil.which("node"):
        return
    merged = {}
    sdir = os.path.join(ROOT, "lib", "fizgig_ko")
    for sub in ("strings", "strings_web"):
        d = os.path.join(sdir, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json") and not fn.startswith("log"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    merged.update(json.load(f))
    _compare(merged, "shipped")


def _web_catalog():
    from fizgig_ko import web
    cat = Catalog()
    cat.add(web.load_catalog())
    return cat


def test_web_catalog_keeps_identity_templates_and_protects_web_ui():
    from fizgig_ko import web
    m = web.load_catalog()
    assert "⚠ {0}" in m and m["⚠ {0}"] == "⚠ {0}"          # a template that only unwraps its pieces
    assert "Web UI" not in m                                 # the page code compares this card title as text
    assert all(en != ko or "{" in en for en, ko in m.items())


def test_web_catalog_translates_assembled_sentences():
    cat = _web_catalog()
    # "⚠ " + a sentence the server builds, with number-agreement ("block{'s' if n != 1 else ''}") dropped
    assert cat.tr("⚠ 3 blocks moved") == "⚠ 블록 3개 이동됨"
    assert cat.tr("1 block moved") == "블록 1개 이동됨"
    assert "노드 팩 기본값 5,120보다 많음" in cat.tr(
        "⚠ ≈ 7,816 tokens at generation (977 per reference), above the pack's 5,120 default")
    plan = ("On this card (24 GB free): a rotation is 2 window(s) x 3 epoch(s) = 6 epochs. "
            "4 rotation(s) = 24 epochs. Checkpoint + preview at epoch 6, 12, 18, 24 (~9 GB each). "
            "The log confirms the plan at Start.")
    out = cat.tr(plan)
    assert "rotation" not in out and "epoch" not in out.replace("에폭", "")
    # a count template must not swallow an unrelated sentence that merely ends the same way
    assert cat.tr("Save clip (WebM)") == "Save clip (WebM)"


def test_web_hook_injects_only_into_the_main_page():
    import types
    from fizgig_ko import web
    sent = []

    class Handler:
        def _send(self, code, body, ctype, extra=()):
            sent.append((code, body, ctype))

    mod = types.SimpleNamespace(Handler=Handler)
    web.apply(mod)
    web.apply(mod)                                           # idempotent: no double wrapping
    page = b'<html><body><meta name="fizgig-token" content="t"><p>Start</p></body></html>'
    Handler()._send(200, page, "text/html; charset=utf-8")
    Handler()._send(200, b"<html><body>other page</body></html>", "text/html")
    Handler()._send(200, b'{"a": 1}', "application/json")
    Handler()._send(404, page, "text/html")
    body = sent[0][1]
    assert body.count(b'<script id="fizgig-ko">') == 1 and body.rfind(b"</body>") > body.find(b'id="fizgig-ko"')
    assert sent[1][1] == b"<html><body>other page</body></html>"      # not the app page
    assert sent[2][1] == b'{"a": 1}' and sent[3][1] == page             # JSON and error pages untouched


def test_web_catalog_trigger_check_verdict_with_pieces():
    cat = _web_catalog()
    # "reads as f | yx | ow | oman" holds " | ", which a template may not swallow: the piecewise fallback has to finish it
    out = cat.tr("✓ Good word. dlorwoman reads as dl | or | woman")
    assert out.startswith("✓ 좋은 단어입니다.") and out.endswith("dl | or | woman") and "reads as" not in out


def test_web_catalog_lucky_status_line():
    cat = _web_catalog()
    assert cat.tr("32 of 32 sliders free to roll") == "슬라이더 32개 중 32개를 굴릴 수 있음"
    assert cat.tr("12 of 32 sliders free to roll, 4 locked or frozen slider(s) left alone") == (
        "슬라이더 32개 중 12개를 굴릴 수 있음, 잠기거나 동결된 슬라이더 4개는 건드리지 않음")
