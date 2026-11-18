# 당근 자동화 (S25 · adb)

## 모임 일정 올리기 — `tools/schedule_post.py`
대상 모임: **나만의 비서 AI 에이전트 구축하기** (S25 `R3CY308BW0Y`, 당근 앱 `com.towneers.www`)

```bash
cd daangn-auto/tools
# 1) 등록 직전까지 자동 (약 1~1.5분). 마지막 버튼은 절대 안 누름
python3 schedule_post.py prepare --date 2026-12-03 --time 19:00 \
    [--template "AI 정보공유 함께 해요"] [--title "새 제목"] [--desc-file 설명.txt] [--allow-dup]
# → JSON: summary_shot(날짜·시간) / desc_shot(설명) / final_shot(옵션 화면) 스크린샷 경로
# 2) 사람(사용자)이 스크린샷 보고 승인하면
python3 schedule_post.py submit      # '일정 만들기' 한 번 → 캘린더 '건너뛰기' → 게시 확인
# 취소: python3 schedule_post.py cancel
```

### 동작
- 지난 일정 **불러오기**로 장소·인원·설명·사진을 복사 → 날짜·시간(·제목·설명)만 바꾼다
  - 기본 템플릿 = 'AI 정보공유 함께 해요'(장소 '명물길 19 지하1층 탐정크루', 6명, 무료)
  - ⚠️ 설명을 안 바꾸면 템플릿 설명의 '진행 시간 2시간 (오후 7시~9시)' 문구도 그대로 → 시간이 다르면 `--desc-file` 로 바꿀 것
- 화면은 웹뷰라 접근성 트리가 없다 → **스크린샷 + 맥 Vision 글자 인식(`tools/ocr`)으로 글자를 찾아서 누른다**(좌표 고정 아님)
- 등록하면 당근이 **모임 전체 채팅방에 자동 공유**한다

### 안전장치
- 모든 탭 직전 당근이 맨 앞인지 확인 (11/18 토스 오탭 사고 재발 방지), 입력 직전에도 확인
- 모임 첫 화면에서 **모임 이름을 확인한 뒤** 들어간 일정 목록만 사용
- 다가오는 일정에 같은 제목·같은 월일 카드가 있으면 중단 (`--allow-dup` 로 무시)
- 날짜·시간은 요약줄 하나만 읽어 숫자로 비교, 다르면 중단
- submit: 동시 실행 잠금 + prepare 30분 이내 + 옵션 화면 확인 + **누르기 전에 준비 기록을 치워** 재실행으로 두 번 등록되지 않음
- 입력기(ADBKeyboard)는 끝나거나 실패해도 삼성 키보드로 원복
- 예상과 다른 화면이면 추측해서 누르지 않고 멈춤 → `{"ok":false,"error":..,"shot":..}`

### 설치·준비 (한 번)
- `cd tools && swiftc -O ocr.swift -o ocr` (맥 Vision, 한국어)
- S25: USB 디버깅 + ADBKeyboard 설치(`adb install --user 0`, 보안폴더 user 150 때문) + `ime enable com.android.adbkeyboard/.AdbIME`

### 시험 기록 (2026-11-18)
- prepare 12/3 19:00 → 55초 / 12/10 20:30 + 제목·설명 교체 → 87초, 화면 확인 ✅
- 11/26 중복 → 차단 ✅ / 준비 없이 submit → 거부 ✅ / submit 실제 등록은 첫 실사용 때 확인
- 교차검토: 코덱스 12건 중 10건 수정, 2건 보류(옵션 화면엔 제목이 안 보여 submit 직전 재검증 불가 → 30분 제한으로 대신 / 1분 단위 분 휠은 당근이 10분 단위라 해당 없음)

화면 구조·좌표 조사 기록은 `FINDINGS.md`
