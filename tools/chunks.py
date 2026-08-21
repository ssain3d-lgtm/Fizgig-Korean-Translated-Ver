"""번역 작업 분배/병합.

  python ko/tools/chunks.py split [--missing]   ko/work/(candidates|missing).json → ko/work/chunks/chunk_NN.json
  python ko/tools/chunks.py merge               ko/work/out/chunk_NN.json → strings/ui.json + strings/log.json (검증 포함)
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


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == "split":
        split("missing.json" if "--missing" in sys.argv else "candidates.json")
    elif len(sys.argv) > 1 and sys.argv[1] == "merge":
        merge()
    else:
        print(__doc__)
