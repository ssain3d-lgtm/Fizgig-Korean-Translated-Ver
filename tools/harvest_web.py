"""Fizgig 8+ 웹 UI 를 헤드리스 브라우저로 돌며 화면의 문구를 수집/점검한다.

  python tools/harvest_web.py [--fizgig PATH]            영어 문구 수집  → work/web_runtime.json
  python tools/harvest_web.py [--fizgig PATH] --check    번역 적용 후 남은 영어 점검 (남으면 종료 코드 1)
  옵션: --shots DIR   탭별 스크린샷 저장,  --no-copy  Fizgig 폴더를 복사하지 않고 그대로 실행

하는 일: Fizgig 폴더를 임시 위치로 복사해 서버를 띄우고(학습은 하지 않음: torch 가 없으면 sandbox_stubs 가
대신합니다), 모델 계열 × 탭 × 학습 종류 × 서브 탭을 전부 눌러 보며 DOM 의 텍스트 노드와
title/placeholder/alt/aria-label 속성을 모읍니다. 숨겨진 패널의 문구도 DOM 에 있으면 잡힙니다.
--check 는 번역기(fizgig_ko)를 켠 채 같은 순회를 하고, 번역기가 못 바꾼 문구(window.__ko.missing())를 보고합니다.

필요: pip install playwright (+ Chromium: 샌드박스에는 /opt/pw-browsers 에 있음)
"""
import argparse
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

KO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(KO_DIR, "work")
TOOLS = os.path.dirname(os.path.abspath(__file__))

SNAPSHOT_JS = r"""
() => {
  const out = {text: [], attr: []};
  const skip = (e) => { for (; e && e.nodeType === 1; e = e.parentElement) {
      const t = e.tagName;
      if (t === 'SCRIPT' || t === 'STYLE' || t === 'NOSCRIPT' || t === 'TEXTAREA' || t === 'PRE' || t === 'TEMPLATE') return true;
      if (e.getAttribute('translate') === 'no') return true; } return false; };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) { if (!skip(n.parentElement) && n.nodeValue && n.nodeValue.trim()) out.text.push(n.nodeValue); }
  for (const e of document.querySelectorAll('*')) {
    if (skip(e)) continue;
    for (const a of ['title', 'placeholder', 'alt', 'aria-label', 'label']) {
      const v = e.getAttribute(a); if (v && v.trim()) out.attr.push(v);
    }
  }
  return out;
}
"""


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _chromium(p):
    try:
        return p.chromium.launch(args=["--no-sandbox"])
    except Exception:
        for path in sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")):
            return p.chromium.launch(executable_path=path, args=["--no-sandbox"])
        raise


def _start_server(root, with_ko):
    port = _free_port()
    tmp = tempfile.mkdtemp(prefix="fizgig_ko_harvest_")
    lines = ["import sys"]
    lines.append("try:\n    import torch  # noqa\nexcept Exception:\n"
                 f"    sys.path.insert(0, {TOOLS!r})\n    import sandbox_stubs\n    sandbox_stubs.install()")
    if with_ko:
        lines.append(f"sys.path.insert(0, {os.path.join(KO_DIR, 'lib')!r})\nimport fizgig_ko")
    with open(os.path.join(tmp, "sitecustomize.py"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    env = dict(os.environ)
    env["PYTHONPATH"] = tmp + os.pathsep + env.get("PYTHONPATH", "")
    # English for a plain harvest (a .pth in the venv would otherwise translate what we are collecting);
    # --check turns the translator on and is told what it could not translate
    if with_ko:
        env.pop("FIZGIG_LANG", None)
    else:
        env["FIZGIG_LANG"] = "en"
    log = open(os.path.join(tmp, "server.log"), "w")
    proc = subprocess.Popen([sys.executable, "fizgig.py", "--web", "--port", str(port)], cwd=root, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1).read(1)
            return proc, port, tmp
        except Exception:
            if proc.poll() is not None:
                break
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("서버가 뜨지 않았습니다:\n" + open(os.path.join(tmp, "server.log")).read()[-1500:])


def _settle(page, ms=450):
    page.wait_for_timeout(ms)


def walk_ui(page, snap, shots=None, after_family=None):
    """Visit every family, tab, training kind and sub-tab, calling snap(label) after each."""
    page.set_default_timeout(4000)
    # the welcome tour opens once the app has booted; it covers the page until it is closed
    try:
        page.wait_for_selector("#welcomeModal.active", timeout=10000)
        _settle(page, 600)
        snap("welcome")
        page.click("#welcomeClose")
        page.wait_for_selector("#welcomeModal.active", state="detached", timeout=3000)
    except Exception:
        pass
    _settle(page, 500)
    families = page.evaluate("() => { const s = document.querySelector('.family-pick'); "
                             "return s ? [...s.options].map(o => o.value) : []; }")
    print("  계열", len(families), families, flush=True)
    tabs = page.eval_on_selector_all("button.tab-item", "els => els.map(e => e.dataset.tab)")
    print("  탭", len(tabs), flush=True)

    def shot(name):
        if shots:
            os.makedirs(shots, exist_ok=True)
            page.screenshot(path=os.path.join(shots, re.sub(r"[^\w.-]+", "_", name) + ".png"), full_page=False)

    for fam in families or [None]:
        print("  >", fam, flush=True)
        if fam:
            try:
                # the pick sits on the Start tab (hidden elsewhere): set it and fire its change event
                page.evaluate("""(v) => { const s = document.querySelector('.family-pick'); s.value = v;
                                          s.dispatchEvent(new Event('change', {bubbles: true})); }""", fam)
                _settle(page, 1200)
            except Exception as e:
                print("  계열 전환 실패", fam, str(e)[:60])
                continue
        for t in tabs:
            try:
                page.click(f'button.tab-item[data-tab="{t}"]')
                _settle(page)
            except Exception:
                continue
            snap(f"{fam}/{t}")
            if fam == families[0] if families else True:
                shot(f"{t}")
            # sub-tabs / sub-modes of a tab
            for sel in ("#tab-%s .ry-tab" % t, "#tab-%s [data-exmode]" % t, "#tab-%s [data-mode]" % t):
                try:
                    for i in range(page.locator(sel).count()):
                        page.locator(sel).nth(i).click(timeout=1000)
                        _settle(page, 250)
                        snap(f"{fam}/{t}/sub{i}")
                except Exception:
                    pass
            if t == "training":
                # the "Kind of training" choice: found by its option values (their text is Korean once translated)
                kind = page.locator("#tab-training select:has(option[value^='Slider'])")
                try:
                    n = kind.first.locator("option").count()
                    for i in range(n):
                        kind.first.select_option(index=i)
                        _settle(page, 500)
                        snap(f"{fam}/training/kind{i}")
                        if fam == (families[0] if families else None):
                            shot(f"training_kind{i}")
                except Exception:
                    pass
        if after_family:
            after_family(fam)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fizgig", default=os.path.dirname(KO_DIR))
    ap.add_argument("--check", action="store_true", help="번역을 켜고 남은 영어를 점검")
    ap.add_argument("--shots")
    ap.add_argument("--no-copy", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    root = os.path.abspath(args.fizgig)
    if not os.path.isfile(os.path.join(root, "src", "fizgig", "web", "static", "index.html")):
        raise SystemExit("Fizgig 8 이상의 폴더가 아닙니다.")
    work_root = root
    tmp_copy = None
    if not args.no_copy:
        tmp_copy = tempfile.mkdtemp(prefix="fizgig_copy_")
        work_root = os.path.join(tmp_copy, "fizgig")
        shutil.copytree(root, work_root, ignore=shutil.ignore_patterns(".git", "venv", "ko", "user_data", "__pycache__",
                                                                       "*.mp4", "models", "node_modules"))
    from playwright.sync_api import sync_playwright
    proc, port, tmp = _start_server(work_root, args.check)
    result = {"text": {}, "attr": {}, "missing": {}}
    out_path = args.out or os.path.join(WORK, "web_missing_runtime.json" if args.check else "web_runtime.json")
    try:
        with sync_playwright() as p:
            b = _chromium(p)
            ctx = b.new_context(viewport={"width": 1500, "height": 950})
            if args.check:
                ctx.add_init_script("window.__KO_COLLECT = true")
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{port}/", wait_until="load")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def snap(label):
                s = page.evaluate(SNAPSHOT_JS)
                for t in s["text"]:
                    result["text"].setdefault(t, set()).add(label.split("/")[1] if "/" in label else label)
                for a in s["attr"]:
                    result["attr"].setdefault(a, set()).add(label.split("/")[1] if "/" in label else label)
                if args.check:
                    for k, n in page.evaluate("window.__ko ? __ko.missing() : []"):
                        result["missing"].setdefault(k, set()).add(label)

            def flush(_fam=None):
                ser = {k: {s: sorted(v) for s, v in d.items()} for k, d in result.items()}
                os.makedirs(WORK, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(ser, f, ensure_ascii=False, indent=1)

            walk_ui(page, snap, args.shots, after_family=flush)
            b.close()
            if errors:
                print("페이지 오류:", errors[:3])
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)
        if tmp_copy:
            shutil.rmtree(tmp_copy, ignore_errors=True)

    ser = {k: {s: sorted(v) for s, v in d.items()} for k, d in result.items()}
    os.makedirs(WORK, exist_ok=True)
    out = out_path
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ser, f, ensure_ascii=False, indent=1)
    if args.check:
        left = {k: v for k, v in ser["missing"].items() if _worth_reporting(k)}
        print(f"번역기가 못 바꾼 영어: {len(left)}개 → {out}")
        return 1 if left else 0
    print(f"수집: 텍스트 {len(ser['text'])}개, 속성 {len(ser['attr'])}개 → {out}")
    return 0


def _worth_reporting(s):
    """False for what is English on purpose: already Korean around a name, or in tools/web_keep_english.json."""
    if not re.search(r"[A-Za-z]{3}", s) or re.search(r"[\uac00-\ud7a3]", s):
        return False
    sys.path.insert(0, TOOLS)
    from extract_web import _keep_english
    keep = _worth_reporting.__dict__.setdefault("keep", _keep_english())
    core = re.sub(r"\s*[:*]+\s*$", "", s.strip())
    return not (keep(s.strip()) or keep(core) or keep(core.strip(" :*")))


if __name__ == "__main__":
    sys.exit(main())
