# Fizgig 한국어 번역 (Fizgig Korean Translation)

[Fizgig](https://github.com/shootthesound/Fizgig) 의 화면 문구를 **실행 시점에** 한국어로 바꿔 주는
애드온입니다. 탭·버튼·라벨·설명문·툴팁·경고창·드롭다운 항목까지 번역합니다.

- **Fizgig 8 이상 (웹 UI)** — 메인 앱이 웹 화면으로 바뀐 버전입니다. 약 **2,700개** 문구를 번역합니다.
- **Gizmo / Fizgig 7 이하 (Tk 창)** — 약 **2,800개** 문구를 번역합니다.

> ### ⚠️ 비공식 커뮤니티 번역입니다
> 이 저장소는 Fizgig 제작자([Peter Neill / shootthesound](https://github.com/shootthesound))와
> **무관하며, 공식 배포판이 아닙니다.** Fizgig 본체는 여기에 포함되어 있지 않습니다.
> Fizgig 는 [공식 저장소](https://github.com/shootthesound/Fizgig)에서 설치하시고,
> 이 번역을 그 위에 얹는 방식입니다.

**Fizgig 소스는 한 글자도 수정하지 않습니다.** 그래서 `update_fizgig.bat`(= `git pull`)로
Fizgig 를 업데이트해도 충돌이 나지 않고, 번역도 영어로 되돌아가지 않습니다.

- 기준 버전: **Fizgig v8.6.0** (웹 UI, MOSS-Image · Flux 3 포함) · Gizmo(Tk)는 v8.6.0 기준
- 더 새로운 Fizgig 에서도 그대로 동작합니다. 새로 추가·변경된 문구만 영어로 보입니다(앱은 정상 동작).

> **Fizgig 를 8 로 올렸더니 한글이 사라졌다면** — 8 부터 메인 앱이 Tk 창에서 웹 화면으로 바뀌어, 예전 번역은
> 더 이상 닿지 않습니다. `ko` 폴더에서 `git pull` 한 뒤 Fizgig 를 **껐다가 다시 켜세요**(설치를 다시 할 필요는 없습니다).
> 브라우저로 보고 있었다면 서버가 다시 뜬 뒤 페이지를 새로고침(Ctrl+F5)하세요.

---

## 설치

Fizgig 가 설치된 폴더(`run_fizgig.bat` 이 있는 폴더) 안에서, **폴더 이름을 `ko` 로** 받으세요.

```
git clone https://github.com/ssain3d-lgtm/Fizgig-Korean-Translated-Ver ko
ko\한글화_설치.bat
```

ZIP 으로 받았다면 압축을 풀어 그 폴더를 Fizgig 폴더 안으로 옮기고(이름은 아무거나 괜찮습니다)
안에 있는 `한글화_설치.bat` 을 더블클릭하면 됩니다.

설치가 끝나면 평소처럼 `run_fizgig.bat` / Gizmo 를 실행하세요. 몇 번 실행해도 안전합니다(멱등).

**Linux / macOS**

```
./install_ko.sh                  # 이 폴더가 Fizgig 폴더 안에 있을 때
./install_ko.sh /path/to/Fizgig  # 그 외
```

## 제거 / 잠시 끄기

| 하고 싶은 것 | 방법 |
|---|---|
| 영어로 되돌리기 | `한글화_제거.bat` (Linux/macOS: `./uninstall_ko.sh`) |
| 이번 실행만 영어로 | 환경변수 `FIZGIG_LANG=en` 을 주고 실행 |
| 웹 UI 를 한 번만 영어로 보기 | 주소 끝에 `?ko=off` 를 붙이기 (예: `http://127.0.0.1:포트/?ko=off`) |

제거는 venv 안에 심은 `.pth` 파일 하나만 지웁니다. Fizgig 쪽에는 아무것도 남지 않습니다.

## 업데이트

| 무엇을 | 어떻게 |
|---|---|
| **Fizgig 본체** | 평소대로 `update_fizgig.bat`. 번역은 그대로 유지됩니다. |
| **번역** | `ko` 폴더에서 `git pull` 후 Fizgig 재시작 |
| **venv 를 새로 만들었을 때** (`install_fizgig.bat` 재실행) | `한글화_설치.bat` 을 한 번 더 |

## 동작 원리

설치는 venv 의 `site-packages/fizgig_ko.pth` **한 줄**뿐입니다. venv 는 git 이 추적하지 않으므로
`git pull` 이 절대 건드리지 않습니다. 이 폴더도 Fizgig 저장소의 `.git/info/exclude` 에 등록되어
`git status` 가 깨끗하게 유지됩니다. 파이썬이 시작할 때 이 줄이 번역 모듈을 불러오고, 모듈은
**두 모듈이 import 되는 순간에만** 훅을 겁니다.

### 웹 UI (Fizgig 8+) — `fizgig.web.server`

- Fizgig 의 웹 서버가 메인 페이지를 내보낼 때 번역 스크립트와 사전을 **응답에 끼워 넣습니다**.
  디스크의 `index.html`/`app.js` 는 수정하지 않습니다.
- 브라우저 안에서 화면의 글자(텍스트·`title`·`placeholder`·`aria-label`·옵션 항목)를 사전으로 바꾸고,
  `MutationObserver` 로 나중에 그려지는 부분(탭 전환, 목록, 상태줄)도 따라갑니다.
- `value`, 입력 중인 텍스트, 로그(`<pre>`), `<textarea>` 는 **건드리지 않습니다**. 앱의 코드가
  글자를 읽어 비교하는 곳(예: `Web UI` 카드 제목)은 번역하지 않도록 보호합니다.
- `{0}` 같은 자리표시자 템플릿(“3 blocks moved” → “블록 3개 이동됨”)은 파이썬·자바스크립트 구현이 똑같이
  동작하며 `tests/test_web_ko.py` 가 둘을 대조합니다.

### Tk 창 (Gizmo · Fizgig 7 이하) — `tkinter`

위젯의 문자열 경로에 끼어들어 사전으로 치환합니다.

- 넣을 때(EN→KO): `Misc._options`(모든 위젯 생성/설정, 메뉴, 메시지박스, 파일 대화상자),
  `ttk._format_optdict`, `Variable.set`, `wm_title`, `Listbox.insert`, `Text.insert`(로그 사전만)
- 읽을 때(KO→EN): `cget`, `StringVar.get`, `Entry.get`, `Listbox.get` — 영어로 되돌려 주므로
  앱 내부 로직과 저장 파일은 전부 영어 기준 그대로 동작합니다.

### 공통

- 둘 다 쓰지 않는 프로세스(학습 서브프로세스 등)에는 아무 영향이 없습니다.
- 사전에 없는 문구는 영어 그대로 보입니다. 패치가 실패해도 앱은 그대로 실행되고,
  오류는 `ko_error.log` 에만 기록됩니다.

## 번역이 어색하면

번역은 Claude(Anthropic)로 일괄 번역한 뒤 용어집 기준으로 검수·수정하고, 실제 화면을 띄워 확인한 결과입니다. 그래도 어색한 곳이 남아 있을 수 있습니다.

`lib/fizgig_ko/strings/zz_overrides.json` 에 `"영어 원문": "원하는 한국어"` 를 추가하고 앱을 다시 켜세요.
이 파일은 마지막에 읽히므로 Tk·웹 두 사전을 모두 덮어씁니다. 좋은 수정은 PR/이슈로 보내 주세요.
(웹 UI 는 페이지에 사전이 실려 가므로 앱을 다시 켠 뒤 브라우저도 새로고침하세요.)

## 알려진 한계

- **(Tk 창만) 입력창에 번역문과 완전히 똑같은 한글을 치면 영어로 바뀝니다.** 읽기 경로의 역매핑(KO→EN) 때문입니다.
  예를 들어 캡션 칸에 정확히 `취소` 라고만 입력하면 `Cancel` 로 들어갑니다. 앞뒤에 다른 글자가 있으면
  괜찮습니다. 문제가 되면 `zz_overrides.json` 에서 해당 항목을 지우거나 `FIZGIG_LANG=en` 으로 실행하세요.
  웹 UI 는 화면 글자만 바꾸고 입력값은 건드리지 않으므로 해당되지 않습니다.
- Fizgig 가 업데이트되면서 문구가 바뀌면 그 문구만 영어로 돌아옵니다(기능 이상 아님).
- 아래는 **의도적으로 번역하지 않습니다**: 음성 녹음용 영어 읽기 지문, 캡션·프롬프트 입력창의 기본값
  (모델에 그대로 전달되는 텍스트), 프롬프트용 단어 목록(LoRA 로얄의 피사체·나이 표현 등), 프리셋/모델 이름,
  파일명·경로·키 이름·옵티마이저 이름 같은 기술 표기, 학습 서브프로세스가 찍는 로그, HTML 갤러리.
  웹 UI 에서는 로그 창(`<pre>`)과 입력 중인 텍스트도 그대로 둡니다.
- 웹 UI 의 새 화면이 서버 코드에서 만든 문구(오류·상태 메시지)는 사전에 문장 단위로 등록되어 있어,
  Fizgig 가 문구를 바꾸면 그 문구만 영어로 돌아옵니다.

## 🐞 버그 신고 전에 꼭 읽어 주세요

**Fizgig 공식 저장소에 이슈를 올리기 전에 `한글화_제거.bat` 으로 번역을 끄고 재현해 보세요.**
번역을 끈 상태에서도 재현되면 → [Fizgig 이슈](https://github.com/shootthesound/Fizgig/issues)로,
번역을 끄면 사라지면 → [이 저장소 이슈](https://github.com/ssain3d-lgtm/Fizgig-Korean-Translated-Ver/issues)로
올려 주세요. 원작자에게 번역 레이어 때문에 생긴 문제가 가지 않도록 하는, 이 프로젝트의 최소한의 예의입니다.

## 새로 생긴 문구 번역하기 (기여자용)

**웹 UI (Fizgig 8+)** — Node.js 와 Playwright 가 필요합니다(`cd tools && npm install`, `pip install playwright`).

```
python tools/extract_web.py --fizgig <Fizgig 폴더>      # 소스(JS·HTML·스키마·파이썬)에서 후보 수집 → work/web_missing.json
python tools/harvest_web.py --fizgig <Fizgig 폴더>      # 실제로 모든 탭을 띄워 화면 문구 수집 → work/web_runtime.json
python tools/extract_web.py --fizgig <Fizgig 폴더>      # (런타임 결과까지 합쳐 다시 계산)
python tools/chunks.py dump-web <파일>                   # 번호가 매겨진 번역 대상 목록
(번역을 work/out_web/*.json 에 {"영어": "한국어"} 로 저장)
python tools/chunks.py merge-web                         # 검증 후 strings_web/web.json 에 병합
python tools/harvest_web.py --fizgig <Fizgig 폴더> --check   # 번역기를 켠 채 남은 영어 점검 (--shots DIR 로 스크린샷)
```

의도적으로 영어로 남기는 것(경로·키·모델명 등)은 `tools/web_keep_english.json` 에 적습니다.
`strings_web/structure.json` 은 코드가 문장을 조립하는 곳의 틀(“⚠ {0}” 등)을 손으로 관리하는 파일입니다.

**Tk 창 (Gizmo · Fizgig 7 이하)**

```
venv\Scripts\python.exe ko\tools\extract.py               # → work/missing.json
venv\Scripts\python.exe ko\tools\chunks.py split --missing
(work/chunks/*.json 을 번역해 work/out/ 에 같은 이름으로 저장)
venv\Scripts\python.exe ko\tools\chunks.py merge          # 검증 후 ui.json / log.json 에 병합
```

영어로 두기로 한 Tk 문구(확장자 패턴, 창 제목 등)는 `tools/tk_keep_english.json` 에 적어 두면 `extract.py` 가 다시 세지 않습니다.

번역 규칙과 용어집은 [`work/GLOSSARY.md`](work/GLOSSARY.md) 에 있습니다.
`merge` 는 자리표시자(`{0}`) 불일치, 한글 누락, 짧은 문구의 중복 번역(역매핑이 깨지는 원인)을 검사합니다.

테스트:

```
venv\Scripts\python.exe ko\tests\run_tests.py
```

## 라이선스

이 저장소는 **Apache License 2.0** 입니다 — [`LICENSE`](LICENSE), [`NOTICE`](NOTICE) 참조.

원작 [Fizgig](https://github.com/shootthesound/Fizgig) 도 Apache-2.0 (Copyright 2026 Peter Neill)
이며, `lib/fizgig_ko/strings/*.json`, `lib/fizgig_ko/strings_web/*.json` 의 **영어 키는 Fizgig 소스에서 추출한 UI 문자열**입니다.
Fizgig 소스 파일 자체는 이 저장소에 포함·수정·재배포되지 않습니다.
"Fizgig" 는 원작 프로젝트의 이름이며, 이 애드온이 무엇을 번역하는지 설명하기 위해서만 사용합니다.

무보증(AS IS)입니다. 자세한 내용은 라이선스 전문을 참고하세요.

---

## English summary

An **unofficial** Korean localization add-on for
[Fizgig](https://github.com/shootthesound/Fizgig) and its bundled Gizmo tool. It ships **no
Fizgig source**: a single `.pth` line in Fizgig's venv installs import hooks that patch the UI at
runtime. Because nothing upstream is modified, `git pull` updates of Fizgig never conflict and never
revert the translation.

- **Fizgig 8+ (web UI):** a hook on `fizgig.web.server` injects a small translator script and the
  dictionary (~2,700 strings) into the main page response; the script rewrites visible text, `title` /
  `placeholder` / `aria-label` and `<option>` labels in the browser and follows later DOM changes. Form
  values, logs (`<pre>`) and anything the page code compares against are left alone. `?ko=off` shows a
  page in English.
- **Gizmo / Fizgig 7 and older (Tk):** a hook on `tkinter` translates ~2,800 strings on the way into
  widgets and maps them back to English on the way out (`cget`, `StringVar.get`, `Entry.get`), so the
  app's own logic and saved files stay English.

If you upgraded to Fizgig 8 and lost the translation: `git pull` in the `ko` folder and restart Fizgig.

Install: clone into the Fizgig folder as `ko`, run `한글화_설치.bat` (or `./install_ko.sh`).
Uninstall: `한글화_제거.bat`. Disable for one run: `FIZGIG_LANG=en`.
Built against Fizgig v8.6.0 (web UI and Gizmo); newer strings simply show in English.

Licensed under Apache-2.0. Derivative of Fizgig (Apache-2.0, Copyright 2026 Peter Neill) —
the English keys in `lib/fizgig_ko/strings/*.json` and `lib/fizgig_ko/strings_web/*.json` are UI strings extracted from its source.
Not affiliated with or endorsed by the Fizgig authors. **Please reproduce bugs with this
layer removed before filing them upstream.**
