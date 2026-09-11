# Fizgig 한국어 번역 (Fizgig Korean Translation)

[Fizgig](https://github.com/shootthesound/Fizgig) 와 함께 들어 있는 **Gizmo** 의 화면 문구를
**실행 시점에** 한국어로 바꿔 주는 애드온입니다. 탭·버튼·라벨·설명문·툴팁·경고창·드롭다운 항목까지
약 **2,300개** 문구를 번역합니다.

> ### ⚠️ 비공식 커뮤니티 번역입니다
> 이 저장소는 Fizgig 제작자([Peter Neill / shootthesound](https://github.com/shootthesound))와
> **무관하며, 공식 배포판이 아닙니다.** Fizgig 본체는 여기에 포함되어 있지 않습니다.
> Fizgig 는 [공식 저장소](https://github.com/shootthesound/Fizgig)에서 설치하시고,
> 이 번역을 그 위에 얹는 방식입니다.

**Fizgig 소스는 한 글자도 수정하지 않습니다.** 그래서 `update_fizgig.bat`(= `git pull`)로
Fizgig 를 업데이트해도 충돌이 나지 않고, 번역도 영어로 되돌아가지 않습니다.

- 기준 버전: **Fizgig v5.7.0** (`4e85cde`)
- 더 새로운 Fizgig 에서도 그대로 동작합니다. 새로 추가·변경된 문구만 영어로 보입니다(앱은 정상 동작).

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

제거는 venv 안에 심은 `.pth` 파일 하나만 지웁니다. Fizgig 쪽에는 아무것도 남지 않습니다.

## 업데이트

| 무엇을 | 어떻게 |
|---|---|
| **Fizgig 본체** | 평소대로 `update_fizgig.bat`. 번역은 그대로 유지됩니다. |
| **번역** | `ko` 폴더에서 `git pull` |
| **venv 를 새로 만들었을 때** (`install_fizgig.bat` 재실행) | `한글화_설치.bat` 을 한 번 더 |

## 동작 원리

`tkinter` 가 import 되는 순간 위젯의 문자열 경로에 끼어들어 사전으로 치환합니다.

- 넣을 때(EN→KO): `Misc._options`(모든 위젯 생성/설정, 메뉴, 메시지박스, 파일 대화상자),
  `ttk._format_optdict`, `Variable.set`, `wm_title`, `Listbox.insert`, `Text.insert`(로그 사전만)
- 읽을 때(KO→EN): `cget`, `StringVar.get`, `Entry.get`, `Listbox.get` — 영어로 되돌려 주므로
  앱 내부 로직과 저장 파일은 전부 영어 기준 그대로 동작합니다.
- 설치는 venv 의 `site-packages/fizgig_ko.pth` **한 줄**뿐입니다. venv 는 git 이 추적하지 않으므로
  `git pull` 이 절대 건드리지 않습니다. 이 폴더도 Fizgig 저장소의 `.git/info/exclude` 에 등록되어
  `git status` 가 깨끗하게 유지됩니다.
- tkinter 를 쓰지 않는 프로세스(학습 서브프로세스 등)에는 아무 영향이 없습니다.
- 사전에 없는 문구는 영어 그대로 보입니다. 패치가 실패해도 앱은 그대로 실행되고,
  오류는 `ko_error.log` 에만 기록됩니다.

## 번역이 어색하면

번역은 Claude(Anthropic)로 일괄 번역한 뒤 용어집 기준으로 검수·수정하고, 실제 화면을 띄워 확인한 결과입니다. 그래도 어색한 곳이 남아 있을 수 있습니다.

`lib/fizgig_ko/strings/zz_overrides.json` 에 `"영어 원문": "원하는 한국어"` 를 추가하고 앱을 다시 켜세요.
이 파일은 알파벳순으로 마지막에 읽히므로 다른 사전을 덮어씁니다. 좋은 수정은 PR/이슈로 보내 주세요.

## 알려진 한계

- **입력창에 번역문과 완전히 똑같은 한글을 치면 영어로 바뀝니다.** 읽기 경로의 역매핑(KO→EN) 때문입니다.
  예를 들어 캡션 칸에 정확히 `취소` 라고만 입력하면 `Cancel` 로 들어갑니다. 앞뒤에 다른 글자가 있으면
  괜찮습니다. 문제가 되면 `zz_overrides.json` 에서 해당 항목을 지우거나 `FIZGIG_LANG=en` 으로 실행하세요.
- Fizgig 가 업데이트되면서 문구가 바뀌면 그 문구만 영어로 돌아옵니다(기능 이상 아님).
- 아래는 **의도적으로 번역하지 않습니다**: 음성 녹음용 영어 읽기 지문, 캡션·프롬프트 입력창의 기본값
  (모델에 그대로 전달되는 텍스트), 프리셋/모델 이름, 학습 서브프로세스가 찍는 로그, HTML 갤러리.

## 🐞 버그 신고 전에 꼭 읽어 주세요

**Fizgig 공식 저장소에 이슈를 올리기 전에 `한글화_제거.bat` 으로 번역을 끄고 재현해 보세요.**
번역을 끈 상태에서도 재현되면 → [Fizgig 이슈](https://github.com/shootthesound/Fizgig/issues)로,
번역을 끄면 사라지면 → [이 저장소 이슈](https://github.com/ssain3d-lgtm/Fizgig-Korean-Translated-Ver/issues)로
올려 주세요. 원작자에게 번역 레이어 때문에 생긴 문제가 가지 않도록 하는, 이 프로젝트의 최소한의 예의입니다.

## 새로 생긴 문구 번역하기 (기여자용)

```
venv\Scripts\python.exe ko\tools\extract.py               # → work/missing.json
venv\Scripts\python.exe ko\tools\chunks.py split --missing
(work/chunks/*.json 을 번역해 work/out/ 에 같은 이름으로 저장)
venv\Scripts\python.exe ko\tools\chunks.py merge          # 검증 후 ui.json / log.json 에 병합
```

번역 규칙과 용어집은 [`work/GLOSSARY.md`](work/GLOSSARY.md) 에 있습니다.
`merge` 는 자리표시자(`{0}`) 불일치, 한글 누락, 짧은 문구의 중복 번역(역매핑이 깨지는 원인)을 검사합니다.

테스트:

```
venv\Scripts\python.exe ko\tests\run_tests.py
```

## 라이선스

이 저장소는 **Apache License 2.0** 입니다 — [`LICENSE`](LICENSE), [`NOTICE`](NOTICE) 참조.

원작 [Fizgig](https://github.com/shootthesound/Fizgig) 도 Apache-2.0 (Copyright 2026 Peter Neill)
이며, `lib/fizgig_ko/strings/*.json` 의 **영어 키는 Fizgig 소스에서 추출한 UI 문자열**입니다.
Fizgig 소스 파일 자체는 이 저장소에 포함·수정·재배포되지 않습니다.
"Fizgig" 는 원작 프로젝트의 이름이며, 이 애드온이 무엇을 번역하는지 설명하기 위해서만 사용합니다.

무보증(AS IS)입니다. 자세한 내용은 라이선스 전문을 참고하세요.

---

## English summary

An **unofficial** Korean localization add-on for
[Fizgig](https://github.com/shootthesound/Fizgig) and its bundled Gizmo tool. It ships **no
Fizgig source**: a single `.pth` line in Fizgig's venv installs an import hook that patches
Tkinter at runtime, translating ~2,300 UI strings on the way into widgets and mapping them
back to English on the way out (`cget`, `StringVar.get`, `Entry.get`), so the app's own logic
and saved files stay English. Because nothing upstream is modified, `git pull` updates of
Fizgig never conflict and never revert the translation.

Install: clone into the Fizgig folder as `ko`, run `한글화_설치.bat` (or `./install_ko.sh`).
Uninstall: `한글화_제거.bat`. Disable for one run: `FIZGIG_LANG=en`.
Built against Fizgig v5.7.0 (`4e85cde`); newer strings simply show in English.

Licensed under Apache-2.0. Derivative of Fizgig (Apache-2.0, Copyright 2026 Peter Neill) —
the English keys in `lib/fizgig_ko/strings/*.json` are UI strings extracted from its source.
Not affiliated with or endorsed by the Fizgig authors. **Please reproduce bugs with this
layer removed before filing them upstream.**
