"""당근 모임 일정 화면 이동·입력 단계들."""
import re
import time

import dg

NAV = (2140, 2310)      # 하단 탭바
BOTTOM = (2050, 2340)   # 하단 큰 버튼(다음 / 일정 만들기)


def _launch():
    dg.adb("shell", "monkey", "-p", dg.PKG, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(4)


def open_schedule_list(moim):
    """어디에 있든 '그 모임'의 일정 목록까지 간다. 모임 이름을 확인한 화면에서 들어간 목록만 인정."""
    if dg.PKG not in dg.foreground():
        _launch()
    verified = False
    for _ in range(9):
        dg.ensure_daangn()
        p, items = dg.read("where")
        if dg.find(items, "다가오는 일정") or dg.find(items, "종료된 일정"):
            if verified:
                return items
            dg.back(2)                       # 어느 모임 목록인지 모름 → 모임 첫 화면으로 나가서 확인
            continue
        if dg.find(items, "챌린지") and dg.find(items, "초대"):      # 모임 첫 화면
            if not dg.find(items, moim, region=(560, 860)):
                dg.back(2)                   # 다른 모임
                continue
            row = dg.find(items, "챌린지")[0]["y"]
            dg.tap_text("일정", exact=True, region=(row - 80, row + 80), items=items, wait=3)
            verified = True
            continue
        if dg.find(items, "커뮤니티", exact=True, region=NAV):       # 탭바가 보이는 화면
            if not dg.find(items, "동네생활", region=(230, 420)):
                dg.tap_text("커뮤니티", exact=True, region=NAV, items=items, wait=3)
                p, items = dg.read("community")
            if not dg.find(items, moim, region=(400, 760)):
                tab = dg.find(items, "모임", exact=True, region=(230, 420))
                if tab:
                    dg.tap(tab[0]["x"], tab[0]["y"], wait=3)
                else:                                  # OCR이 '동네생활 모임 카페…'를 한 덩어리로 읽는 경우
                    row = dg.find(items, "동네생활", region=(230, 420))
                    if not row or "모임" not in row[0]["t"]:
                        raise dg.StepError(f"커뮤니티 상단 '모임' 탭을 못 찾음 → {p}")
                    dg.tap(342, row[0]["y"], wait=3)   # '모임' 탭 고정 위치(동네생활 바로 오른쪽)
                p, items = dg.read("moim_tab")
            dg.tap_text(moim, region=(400, 760), items=items, wait=4)
            continue
        dg.back(2)
    raise dg.StepError("모임 일정 목록 화면까지 못 감")


def upcoming_has(items, title, when):
    """다가오는 일정 카드 중 '같은 제목 + 같은 월·일' 카드가 있는지(카드 단위로 묶어서 비교)."""
    top = dg.find(items, "다가오는 일정")
    end = dg.find(items, "종료된 일정")
    if not top:
        return False
    y0, y1 = top[0]["y"], (end[0]["y"] if end else 2100)
    for t in dg.find(items, title, region=(y0, y1)):
        card = [i for i in items if i["x"] < 200 and t["y"] - 40 <= i["y"] <= t["y"] + 230]
        txt = " ".join(i["t"] for i in sorted(card, key=lambda i: i["y"]))
        if re.search(rf"(^|\D){when.month}\D*월", txt) and re.search(rf"(^|\D){when.day}(\D|$)", txt.split("월", 1)[-1]):
            return True
    return False


def start_new_form():
    dg.tap_text("일정 만들기", region=BOTTOM, wait=3)
    p, items = dg.read("form_open")
    if dg.find(items, "새로 작성"):              # 임시저장 확인창
        dg.tap_text("새로 작성", items=items, wait=2)
    dg.wait_text("불러오기", name="form")


def load_template(title):
    dg.tap_text("불러오기", region=(400, 560), wait=3)
    dg.wait_text("지난 일정 불러오기", name="load_sheet")
    for _ in range(4):
        p, items = dg.read("load_list")
        hits = dg.find(items, title, region=(880, 2300))
        if hits:
            dg.tap(hits[0]["x"], hits[0]["y"], wait=3)
            break
        dg.swipe(540, 2000, 540, 1100)
    else:
        raise dg.StepError(f"불러오기 목록에 '{title}' 일정이 없어요")
    dg.wait_text("장소", name="loaded")       # 불러오면 달력 쪽으로 자동 스크롤된다
    scroll_top()
    p, items = dg.read("loaded_top")
    if not dg.find(items, title, region=(200, 460)):
        raise dg.StepError(f"불러온 제목이 '{title}'가 아니에요 → {p}")


def set_title(old, new):
    _, items = dg.read("title_before")
    dg.tap_text(old, region=(200, 460), items=items, wait=1.8)
    dg.type_text(new, clear=True)
    p, items = dg.read("title_after")
    if not dg.find(items, new, region=(200, 460)):
        raise dg.StepError(f"제목이 '{new}'로 안 바뀜 → {p}")


def scroll_top():
    for _ in range(3):
        dg.swipe(540, 700, 540, 1900, ms=300, wait=1)


def verify_summary(when):
    """'날짜 및 시간' 줄 하나만 읽어 숫자로 비교(다른 글자에 우연히 들어 있는 날짜로 통과 방지)."""
    scroll_top()
    p, items = dg.read("summary")
    lab = dg.find(items, "날짜 및 시간")
    if not lab:
        raise dg.StepError(f"'날짜 및 시간' 줄을 못 찾음 → {p}")
    row = " ".join(i["t"] for i in items if abs(i["y"] - lab[0]["y"]) < 40)
    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일.*?(오전|오후)\s*(\d{1,2}):(\d{2})", row)
    if not m:
        raise dg.StepError(f"날짜·시간 줄을 못 읽음 '{row}' → {p}")
    mo, d, ap, h, mi = int(m[1]), int(m[2]), m[3], int(m[4]), int(m[5])
    h24 = (h % 12) + (12 if ap == "오후" else 0)
    if (mo, d, h24, mi) != (when.month, when.day, when.hour, when.minute):
        raise dg.StepError(f"날짜·시간 불일치: 화면 '{row}' / 기대 {when:%m-%d %H:%M} → {p}")
    return p


def set_desc(text):
    p, items = dg.read("desc_before")
    anchor = dg.find(items, "본문 작성하기")
    if not anchor:
        raise dg.StepError(f"설명 화면 기준('AI로 본문 작성하기')을 못 찾음 → {p}")
    y0 = anchor[0]["y"] + 80
    dg.tap(300, y0 + 40, wait=1.8)           # 설명 칸 첫 줄(기준 바로 아래, 입력란 안쪽)
    dg.type_text(text, clear=True)
    p, items = dg.read("desc_after")
    first = text.splitlines()[0][:10]
    if not dg.find(items, first, region=(y0 - 20, 1450)):
        raise dg.StepError(f"설명이 안 바뀜 → {p}")
