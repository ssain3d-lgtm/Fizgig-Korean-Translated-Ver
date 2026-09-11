# Fizgig 한글화 번역 지침 (번역 에이전트용)

Fizgig는 Flux 2 Klein 9B / Krea 2 / MiniMax H3 모델용 **LoRA 학습 데스크톱 앱**(Tkinter)이고,
Gizmo는 그 부속 도구(영상/음성 클립 자르기, 녹음)입니다. 사용자는 한국의 AI 이미지·영상 생성 취미/전문가입니다.

## 출력 형식 (엄수)
- 입력 JSON의 **키(영어 원문)를 글자 하나 바꾸지 말고** 그대로 두고, 값만 한국어로 채웁니다.
- 출력은 `{"영어 원문": "한국어 번역", ...}` 형태의 **순수 JSON** 파일로 저장합니다. 설명문·주석·코드펜스 금지.
- 번역하면 안 되는 항목은 값을 빈 문자열 `""` 로 둡니다:
  코드 식별자, ttk 스타일명, 파일 확장자/경로, CLI 플래그, 폰트명, 모델 저장소 ID(`MiaoshouAI/...`),
  내부 설정값(소문자 한 단어), 의미를 알 수 없는 단편 조각.
- `{0}` `{1}` 같은 자리표시자는 **개수·번호를 그대로** 유지합니다(순서는 한국어 어순에 맞게 바꿔도 됨).
  자리표시자에는 숫자, 파일명, 경로, 에러 메시지 등 무엇이든 들어옵니다.
- 줄바꿈 `\n`, 앞뒤 공백, 끝의 콜론(`:`)·마침표·말줄임표(`…`/`...`), 이모지·기호(⬆ ✓ ✗ ● ▶ — · ×) 를 보존합니다.
  예: `"Seed:"` → `"시드:"`, `"Browse…"` → `"찾아보기…"`, `"  ✓ done\n"` → `"  ✓ 완료\n"`.
- 키에 `\n` 이 들어 있으면 값에도 비슷한 위치에 `\n` 을 넣습니다(라벨의 줄바꿈 레이아웃).

## 어조
- 버튼·라벨·탭·섹션 제목: 짧은 명사형. (`Start Training` → `학습 시작`, `Refresh` → `새로고침`)
- 메시지·설명·툴팁: `~합니다 / ~하세요` 격식체. 군더더기 없이 자연스럽게. 원문의 유머는 가볍게 살리되 의미 전달이 우선.
- 버튼/짧은 라벨은 원문보다 길어지지 않게. 긴 설명문은 의미가 통하면 약간 줄여도 됩니다.
- 원문이 다른 UI 요소를 따옴표로 가리키면(`set 'DiT (reference)' on the Preferences tab`) 아래 용어집의 번역명을 그대로 씁니다.

## 고정 용어집 (반드시 일치시킬 것)
| 영어 | 한국어 |
|---|---|
| Fizgig, Gizmo, Klein, Krea 2, MiniMax H3, Flux, RunPod, Whisper, Qwen, Florence, ComfyUI, LoRA, LoKr, DiT, VAE, CUDA, GPU, VRAM, RAM, fp8, bf16, int8, nf4, ffmpeg, safetensors, HTML, JSON, PNG, GIF, MP4, WAV | 그대로 (영문 유지) |
| Start (탭) | 시작 |
| Image Prep | 이미지 준비 |
| Captions / caption | 캡션 |
| Samples / sample (preview) | 샘플 |
| Training / train | 학습 / 학습하다 |
| Profiler / profile | 프로파일러 / 프로파일 |
| Repair Studio | 리페어 스튜디오 |
| LoRA the Explorer | LoRA 탐색기 |
| LoRA Royale | LoRA 로얄 |
| Extract / extraction | 추출 |
| Metadata | 메타데이터 |
| Preferences | 환경설정 |
| About | 정보 |
| Queue / queued / Training queue | 대기열 / 대기열에 추가됨 / 학습 대기열 |
| Browse… | 찾아보기… |
| Cancel | 취소 |
| Stop | 중지 |
| Close | 닫기 |
| Save / Load | 저장 / 불러오기 |
| Update (버전) / Update (갱신) | 업데이트 / 업데이트 |
| Refresh | 새로고침 |
| Reset | 초기화 |
| Remove / Delete / Clear | 제거 / 삭제 / 지우기 |
| Open / Export / Import | 열기 / 내보내기 / 가져오기 |
| Preset | 프리셋 |
| Dataset | 데이터셋 |
| Trigger word | 트리거 워드 |
| Prompt / negative prompt | 프롬프트 / 네거티브 프롬프트 |
| Seed | 시드 |
| Epoch(s) | 에폭 |
| Step(s) | 스텝 |
| Batch size | 배치 크기 |
| Learning rate (LR) | 학습률 (LR) |
| Rank / Network Dim / Alpha | 랭크 / 네트워크 차원(Rank) / 알파 |
| Timestep(s) | 타임스텝 |
| Noise / low-noise / high-noise | 노이즈 / 저노이즈 / 고노이즈 |
| Resolution | 해상도 |
| Checkpoint | 체크포인트 |
| State (resume state) | 상태 저장본 |
| Resume / Pause | 재개 / 일시정지 |
| Gradient checkpointing | 그래디언트 체크포인팅 |
| Gradient accumulation | 그래디언트 누적 |
| Blocks / Blocks swap / Blocks to Train | 블록 / 블록 스왑 / 학습할 블록 |
| Offloading | 오프로딩 |
| Text encoder | 텍스트 인코더 |
| Cache / caching (latents) | 캐시 / 캐싱 |
| Face crop / face detection | 얼굴 크롭 / 얼굴 감지 |
| Likeness | 닮음 정도 |
| Identity (프리셋/모드) | 아이덴티티 |
| Style / Composition | 스타일 / 구도 |
| Style+Composition | 스타일+구도 |
| Reference (image/DiT) | 레퍼런스 |
| Donor LoRA / Primary LoRA | 도너 LoRA / 기본 LoRA |
| Strength | 강도 |
| Variant(s) / mutation(s) | 변형 / 변이 |
| Seed travel / prompt morph | 시드 트래블 / 프롬프트 모프 |
| Interpolation / Crossfade | 보간 / 크로스페이드 |
| Waypoint(s) | 웨이포인트 |
| Frame(s) / clip(s) / take(s) / segment(s) | 프레임 / 클립 / 테이크 / 구간 |
| Cut (scene cut) | 컷 |
| Transcribe / transcription | 전사 / 전사 결과 |
| Microphone / recording | 마이크 / 녹음 |
| Delivery (말하는 톤) | 전달 톤 |
| Auto-chop | 자동 분할 |
| Turbo (LoRA) | 터보 |
| Preview | 미리보기 |
| Console / log | 콘솔 / 로그 |
| Pod (RunPod) | 팟 |
| Tip jar / coffee | 후원 / 커피 한 잔 |
| Workbench | 워크벤치 |
| Edit model | 편집 모델 |
| Full Model (학습할 블록 범위 옵션) | 전체 모델 |
| Fine-tune / fine-tuning (v5.0.0+, 베이스 모델 자체 학습) | 파인튜닝 |
| Rotation cycle / window | 로테이션 주기 / 윈도우 |
| component mode / block mode | 컴포넌트 모드 / 블록 모드 |
| Checkpoint to LoRA | 체크포인트 → LoRA |
| Regularisation images | 정규화 이미지 |
| Training adapter | 학습 어댑터 |
| Training mode | 학습 모드 |
| Refiner (text token refiner) | 리파이너 |
| Baseline / Tweaked (리페어 스튜디오) | 원본 / 조정본 |
| Library / bank (리페어 스튜디오 블록 라이브러리) | 라이브러리 / 뱅크 |
| Pass (렌더당 모델 패스) | 패스 |
| Keyframe | 키프레임 |
| Optimised Likeness Learning | 최적화 닮음 학습 |
| Train / Queue Train | 학습 / 대기열에 학습 추가 |
| Ready. / Done. / Busy | 준비됨. / 완료. / 작업 중 |
| Off / On / Auto / None / All / Custom | 끔 / 켬 / 자동 / 없음 / 전체 / 사용자 지정 |
| Normal / Strong / Fast / Slow | 보통 / 강함 / 빠름 / 느림 |
| Yes / No / OK | 예 / 아니요 / 확인 |

## 주의
- 같은 영어 단어가 여러 곳에 쓰이면 한 가지 번역으로 통일하세요(위 표 우선).
- `Update` 가 `⬆ Update Available` 식이면 `⬆ 업데이트 있음`. 버튼 `Update` 는 `업데이트`.
- `Krea 2 RAW DiT`, `Klein 9B`, `H3` 같은 모델 표기는 그대로.
- `fine-tune` 은 v5.0.0 에서 들어온 **베이스 모델 자체 학습**이라 `파인튜닝` 으로 옮깁니다.
  기존 `Full Model`(LoRA 안에서 학습할 블록 범위를 고르는 옵션 값, `전체 모델`)과 혼동하지 마세요.
- 영어 복수 접미사 자리표시자(`clip{1}` 의 `{1}` = `s` 또는 빈 값)는 한국어에 불필요하지만
  `merge` 가 자리표시자 누락을 거부하므로, 기존 항목들처럼 수량 뒤에 그대로 둡니다(`클립 {0}개{1}`).
- 영어 관용구(`More soup, vicar?` 같은 샘플 문장, 인용구)가 **읽기 지문/샘플 대사**로 보이면 `""` 로 비웁니다.
