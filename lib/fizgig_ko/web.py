"""Fizgig 8+ 웹 UI 번역.

Fizgig 8 부터 메인 앱은 Tk 창이 아니라 로컬 서버(fizgig.web.server)가 내보내는 웹 페이지입니다.
서버가 메인 페이지를 응답하는 순간 번역 스크립트(web_ko.js)와 사전을 페이지 끝에 끼워 넣고,
브라우저 쪽에서 화면의 문구를 한국어로 바꿉니다. Fizgig 의 파일은 한 글자도 수정하지 않습니다.

  - 훅 지점: fizgig.web.server.Handler._send (200 / text/html / 메인 페이지 표식이 있을 때만)
  - 사전: strings_web/*.json  +  strings/zz_overrides.json (Tk 와 웹이 같은 오버라이드 파일을 씁니다)
  - 실패해도 앱은 그대로 동작합니다(영어로 보일 뿐). 오류는 ko_error.log 에만 기록됩니다.
"""
import json
import os
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(_HERE))                      # .../ko
WEB_STRINGS_DIR = os.path.join(_HERE, "strings_web")
OVERRIDES = os.path.join(_HERE, "strings", "zz_overrides.json")
JS_PATH = os.path.join(_HERE, "web_ko.js")

#: only the app's own page carries this (the other text/html answers are reports and galleries)
PAGE_MARK = b'name="fizgig-token"'

#: Strings the page's own code compares against its text, so they must stay English.
#: ("Web UI" is the title the Preferences code looks a card up by.)
PROTECTED = ("Web UI",)

_tag = None


def log_error(where):
    try:
        with open(os.path.join(BASE_DIR, "ko_error.log"), "a", encoding="utf-8") as f:
            f.write(f"--- {where}\n{traceback.format_exc()}\n")
    except Exception:
        pass


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_catalog():
    """{english: korean} for the web UI: every strings_web/*.json, then the user's overrides."""
    merged = {}
    if os.path.isdir(WEB_STRINGS_DIR):
        for name in sorted(os.listdir(WEB_STRINGS_DIR)):
            if name.lower().endswith(".json"):
                merged.update(_load_json(os.path.join(WEB_STRINGS_DIR, name)))
    merged.update(_load_json(OVERRIDES))
    # an identity entry is dead weight unless it is a template ("⚠ {0}"): that one lets the pieces it
    # captures be translated on their own
    return {en: ko for en, ko in merged.items()
            if isinstance(en, str) and isinstance(ko, str) and ko and en not in PROTECTED
            and (en != ko or "{" in en)}


def _script_json(obj):
    """JSON that is safe inside an inline <script>."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (s.replace("</", "<\\/").replace("<!--", "<\\!--")
             .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build_tag():
    """The <script> element that carries the dictionary and the translator (built once)."""
    global _tag
    if _tag is None:
        with open(JS_PATH, encoding="utf-8") as f:
            js = f.read().replace("</script", "<\\/script")
        text = ('<script id="fizgig-ko">window.__KO_CAT=' + _script_json({"m": load_catalog()}) + ";\n"
                + js + "\n</script>\n")
        _tag = text.encode("utf-8")
    return _tag


def inject(page):
    """The page with the translator added before </body> (bytes in, bytes out)."""
    tag = build_tag()
    i = page.rfind(b"</body>")
    return page[:i] + tag + page[i:] if i >= 0 else page + tag


def apply(server_module):
    """Hook fizgig.web.server's request handler. Raises if the handler has changed shape; the
    caller logs it and the page simply stays English."""
    handler = getattr(server_module, "Handler", None)
    send = getattr(handler, "_send", None)
    if send is None:
        raise RuntimeError("fizgig.web.server.Handler._send not found (Fizgig changed its web server)")
    if getattr(send, "_ko_hooked", False):
        return

    def _send(self, code, body, ctype, extra=()):
        try:
            if (code == 200 and isinstance(body, (bytes, bytearray)) and str(ctype).startswith("text/html")
                    and PAGE_MARK in body):
                body = inject(bytes(body))
        except Exception:
            log_error("web.inject")
        return send(self, code, body, ctype, extra)

    _send._ko_hooked = True
    handler._send = _send
