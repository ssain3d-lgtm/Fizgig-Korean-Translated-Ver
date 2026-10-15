"""번역 작업 분배/병합.

  python ko/tools/chunks.py split [--missing]   ko/work/(candidates|missing).json → ko/work/chunks/chunk_NN.json
  python ko/tools/chunks.py merge               ko/work/out/chunk_NN.json → strings/ui.json + strings/log.json (검증 포함)

웹 UI(Fizgig 8+) 용 — tools/extract_web.py 가 만든 work/web_missing.json · web_reuse.json 을 씁니다:
  python ko/tools/chunks.py dump-web [FILE]     번역할 문구를 출처별로 읽기 좋게 덤프 (+ Tk 사전의 비슷한 번역을 힌트로)
  python ko/tools/chunks.py merge-web           ko/work/out_web/*.json (+ web_reuse.json) → strings_web/web.json (검증 포함)
"""
import json
import os
import re
import sys

KO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(KO_DIR, "work")
CHUNKS = os.path.join(WORK, "chunks")
OUT = os.path.join(WORK, "out")
STRINGS = os.path.join(KO_DIR, "lib", "fizgig_ko", "strings")
PH = re.compile(r"\{(\d+)\}")

MAX_CHARS = 6500
MAX_ITEMS = 110


def _loc(v):
    c = v["ctx"][0]
    f, ln = c.split("@")[1].rsplit(":", 1)
    return (f, int(ln))


def split(src):
    data = json.load(open(os.path.join(WORK, src), encoding="utf-8"))
    items = sorted(data.items(), key=lambda kv: _loc(kv[1]))
    os.makedirs(CHUNKS, exist_ok=True)
    for fn in os.listdir(CHUNKS):
        os.remove(os.path.join(CHUNKS, fn))
    chunk, size, n = {}, 0, 0

    def flush():
        nonlocal chunk, size, n
        if chunk:
            with open(os.path.join(CHUNKS, f"chunk_{n:02d}.json"), "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=1)
            n += 1
            chunk, size = {}, 0

    for en, v in items:
        if size + len(en) > MAX_CHARS or len(chunk) >= MAX_ITEMS:
            flush()
        chunk[en] = {"ctx": v["ctx"][0].split("@")[0] + (" (log)" if v["log"] else ""), "ko": ""}
        size += len(en)
    flush()
    print(f"{len(items)}개 → {n}개 청크 ({CHUNKS})")


def merge():
    cand = json.load(open(os.path.join(WORK, "candidates.json"), encoding="utf-8"))
    ui = json.load(open(os.path.join(STRINGS, "ui.json"), encoding="utf-8")) if os.path.exists(os.path.join(STRINGS, "ui.json")) else {}
    log = json.load(open(os.path.join(STRINGS, "log.json"), encoding="utf-8")) if os.path.exists(os.path.join(STRINGS, "log.json")) else {}
    problems = []
    added = 0
    for fn in sorted(os.listdir(OUT)):
        if not fn.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
        except Exception as e:
            problems.append(f"{fn}: JSON 오류 {e}")
            continue
        for en, ko in data.items():
            if isinstance(ko, dict):
                ko = ko.get("ko", "")
            if not isinstance(ko, str) or not ko.strip() or ko == en:
                continue
            if sorted(PH.findall(en)) != sorted(set(PH.findall(ko))) and set(PH.findall(ko)) - set(PH.findall(en)):
                problems.append(f"{fn}: 자리표시자 불일치 {en!r} → {ko!r}")
                continue
            if set(PH.findall(en)) != set(PH.findall(ko)):
                problems.append(f"{fn}: 자리표시자 누락 {en!r} → {ko!r}")
                continue
            if not re.search(r"[가-힣]", ko):
                problems.append(f"{fn}: 한글 없음 {en!r} → {ko!r}")
                continue
            target = log if cand.get(en, {}).get("log") else ui
            if target.get(en) != ko:
                added += 1
            target[en] = ko
    # short strings must map to unique Korean (reverse lookup on get()/cget())
    rev = {}
    for en, ko in ui.items():
        if len(en) <= 40 and "{" not in en:
            if ko in rev and rev[ko] != en:
                problems.append(f"중복 번역(짧은 문구): {rev[ko]!r} 와 {en!r} → {ko!r}")
            rev.setdefault(ko, en)
    os.makedirs(STRINGS, exist_ok=True)
    with open(os.path.join(STRINGS, "ui.json"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(ui.items())), f, ensure_ascii=False, indent=1)
    with open(os.path.join(STRINGS, "log.json"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(log.items())), f, ensure_ascii=False, indent=1)
    print(f"ui.json {len(ui)}개, log.json {len(log)}개 (신규/변경 {added}개)")
    if problems:
        with open(os.path.join(WORK, "merge_problems.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(problems))
        print(f"문제 {len(problems)}건 → {os.path.join(WORK, 'merge_problems.txt')}")
        for p in problems[:30]:
            print("  ", p)


# -- 웹 UI (Fizgig 8+) -------------------------------------------------------------------------------------
OUT_WEB = os.path.join(WORK, "out_web")
STRINGS_WEB = os.path.join(KO_DIR, "lib", "fizgig_ko", "strings_web")
WEB_JSON = os.path.join(STRINGS_WEB, "web.json")
#: 페이지 코드가 화면 글자와 직접 비교하는 문구는 번역하면 앱이 깨진다 (lib/fizgig_ko/web.py 의 PROTECTED 와 같음)
WEB_PROTECTED = ("Web UI",)
#: 한글이 없어도 되는 번역: 낱글자 구분 기호 ("Page 1 of 5" 의 가운데 "of" → "/")
WEB_NO_HANGUL_OK = {"of": "/"}


def dump_web(path=None, hint_cutoff=0.78):
    import difflib
    miss = json.load(open(os.path.join(WORK, "web_missing.json"), encoding="utf-8"))
    tk = {}
    for fn in ("ui.json", "log.json", "zz_overrides.json"):
        p = os.path.join(STRINGS, fn)
        if os.path.exists(p):
            tk.update(json.load(open(p, encoding="utf-8")))
    norm = lambda t: re.sub(r"\s+", " ", t.strip())
    tkn = {norm(k): v for k, v in tk.items() if v}
    keys = list(tkn)

    def order(item):
        s, e = item
        return (e["src"][0].split(":")[0], e["src"][0], s.lower())

    lines = []
    for i, (en, e) in enumerate(sorted(miss.items(), key=order), 1):
        lines.append(f"[{i}] {','.join(e['src'][:3])}")
        lines.append("EN " + repr(en))
        m = difflib.get_close_matches(norm(en), keys, n=1, cutoff=hint_cutoff)
        if m:
            r = difflib.SequenceMatcher(None, norm(en), m[0]).ratio()
            lines.append(f"REUSE({r:.2f}) OLD_EN {m[0]!r}\n      OLD_KO {tkn[m[0]]!r}")
        lines.append("")
    out = path or os.path.join(WORK, "web_dump.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"{len(miss)}개 → {out}")


def plural_suffixes(en):
    """Placeholders of `en` that tools/extract_web.py found to be a plural suffix: a conditional that yields
    "s" or "" (`${n === 1 ? "" : "s"}`). Only those may be left out of the Korean."""
    cands = _web_candidates()
    return {str(n) for n in cands.get(en, {}).get("plural", [])}


_CANDS = None


def _web_candidates():
    global _CANDS
    if _CANDS is None:
        path = os.path.join(WORK, "web_candidates.json")
        _CANDS = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    return _CANDS


def merge_web():
    web = json.load(open(WEB_JSON, encoding="utf-8")) if os.path.exists(WEB_JSON) else {}
    problems, added = [], 0
    incoming = {}
    reuse_path = os.path.join(WORK, "web_reuse.json")
    if os.path.exists(reuse_path):
        for en, ko in json.load(open(reuse_path, encoding="utf-8")).items():
            incoming[en] = ("web_reuse.json", ko)
    if os.path.isdir(OUT_WEB):
        for fn in sorted(os.listdir(OUT_WEB)):
            if fn.endswith(".json"):
                try:
                    data = json.load(open(os.path.join(OUT_WEB, fn), encoding="utf-8"))
                except Exception as e:
                    problems.append(f"{fn}: JSON 오류 {e}")
                    continue
                for en, ko in data.items():
                    incoming[en] = (fn, ko)
    for en, (fn, ko) in incoming.items():
        if isinstance(ko, dict):
            ko = ko.get("ko", "")
        if not isinstance(ko, str) or not ko.strip() or ko == en:
            continue
        if en in WEB_PROTECTED:
            problems.append(f"{fn}: 보호 문구는 번역하지 않습니다 {en!r}")
            continue
        # 영어의 복수 접미사("clip{1}" 의 {1} = "s" 또는 "")는 한국어에 필요 없습니다. 웹 사전에서는 생략해야
        # "클립 3개s" 처럼 s 가 그대로 보이지 않습니다. 생략할 수 있는 것은 그것뿐입니다.
        missing = set(PH.findall(en)) - set(PH.findall(ko))
        if set(PH.findall(ko)) - set(PH.findall(en)) or missing - plural_suffixes(en):
            problems.append(f"{fn}: 자리표시자 불일치 {en!r} → {ko!r}")
            continue
        if not re.search(r"[가-힣]", ko) and WEB_NO_HANGUL_OK.get(en) != ko:
            problems.append(f"{fn}: 한글 없음 {en!r} → {ko!r}")
            continue
        for n in plural_suffixes(en):                         # "클립 3개s" 방지: 복수 접미사는 한국어에서 뺀다
            ko = ko.replace("{%s}" % n, "", 1)
        if web.get(en) != ko:
            added += 1
        web[en] = ko
    os.makedirs(STRINGS_WEB, exist_ok=True)
    with open(WEB_JSON, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(web.items())), f, ensure_ascii=False, indent=1)
    print(f"web.json {len(web)}개 (신규/변경 {added}개)")
    if problems:
        with open(os.path.join(WORK, "merge_problems.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(problems))
        print(f"문제 {len(problems)}건 → {os.path.join(WORK, 'merge_problems.txt')}")
        for p in problems[:30]:
            print("  ", p)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == "split":
        split("missing.json" if "--missing" in sys.argv else "candidates.json")
    elif len(sys.argv) > 1 and sys.argv[1] == "merge":
        merge()
    elif len(sys.argv) > 1 and sys.argv[1] == "dump-web":
        dump_web(sys.argv[2] if len(sys.argv) > 2 else None)
    elif len(sys.argv) > 1 and sys.argv[1] == "merge-web":
        merge_web()
    else:
        print(__doc__)
