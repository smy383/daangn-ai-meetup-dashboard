"""일정 작성 화면의 달력·시간 휠 조작."""
import re

import dg
import nav

ARROW_NEXT_X = 992   # 달력 머리 'YYYY년 M월' 오른쪽 '>' 버튼 x


def _weekday_row(items):
    sat = dg.find(items, "토", exact=True)
    sun = dg.find(items, "일", exact=True)
    for s in sat:
        for u in sun:
            if abs(s["y"] - u["y"]) < 30 and u["x"] < 200 and s["x"] > 880:
                return s["y"]
    return None


def _header(items):
    for i in items:
        m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월", i["t"])
        if m:
            return int(m.group(1)), int(m.group(2)), i["y"]
    return None


def set_date(when):
    nav.scroll_top()
    p, items = dg.read("date_0")
    if _weekday_row(items) is None:
        dg.tap_text("날짜 및 시간", items=items, wait=2)
        nav.scroll_top()
        p, items = dg.read("date_1")
    hd = _header(items)
    if not hd:
        raise dg.StepError(f"달력 머리(YYYY년 M월)를 못 찾음 → {p}")
    diff = (when.year * 12 + when.month) - (hd[0] * 12 + hd[1])
    if diff < 0 or diff > 6:
        raise dg.StepError(f"달력 이동 범위 밖 ({hd[0]}.{hd[1]} → {when.year}.{when.month})")
    for _ in range(diff):
        dg.tap(ARROW_NEXT_X, hd[2], wait=1.5)
    p, items = dg.read("date_month")
    hd = _header(items)
    if not hd or (hd[0], hd[1]) != (when.year, when.month):
        raise dg.StepError(f"{when.year}년 {when.month}월로 못 넘김 → {p}")
    wy = _weekday_row(items)
    label = [i for i in dg.find(items, "시간", exact=True) if i["x"] < 250 and i["y"] > (wy or 0)]
    if wy is None or not label:
        raise dg.StepError(f"달력 칸 범위를 못 찾음 → {p}")
    day = dg.find(items, str(when.day), exact=True, region=(wy + 40, label[0]["y"] - 40))
    if len(day) != 1:
        raise dg.StepError(f"{when.day}일 칸을 정확히 못 찾음({len(day)}개) → {p}")
    dg.tap(day[0]["x"], day[0]["y"], wait=1.5)


def _wheel(items, x0, x1):
    return sorted([i for i in items if x0 <= i["x"] < x1 and 1450 <= i["y"] <= 2060],
                  key=lambda i: i["y"])


def _center(col, cy):
    return min(col, key=lambda i: abs(i["y"] - cy)) if col else None


def _num(s):
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def set_time(when):
    p, items = dg.read("time_0")
    lab = [i for i in dg.find(items, "시간", exact=True) if i["x"] < 250]
    if not lab:
        raise dg.StepError(f"'시간' 칸을 못 찾음 → {p}")
    dg.tap(830, lab[0]["y"], wait=2)
    dg.wait_text("확인", region=(2050, 2340), name="wheel")
    want_ap = "오전" if when.hour < 12 else "오후"
    want_h = when.hour % 12 or 12
    want_m = when.minute
    cy = None
    for step in range(30):
        p, items = dg.read("wheel_step")
        hours = _wheel(items, 350, 720)
        if cy is None:
            if len(hours) != 3:          # 위·가운데·아래 3개가 다 보여야 가운데(선택값)를 정확히 안다
                raise dg.StepError(f"시간 휠 숫자 {len(hours)}개만 읽힘 → {p}")
            cy = hours[1]["y"]
        aps, mins = _wheel(items, 0, 350), _wheel(items, 720, 1080)
        ap, h, m = _center(aps, cy), _center(hours, cy), _center(mins, cy)
        if not (ap and h and m):
            raise dg.StepError(f"휠 값을 못 읽음 → {p}")
        if want_ap not in ap["t"]:
            other = [i for i in aps if want_ap in i["t"]]
            if not other:
                raise dg.StepError(f"'{want_ap}'를 휠에서 못 찾음 → {p}")
            dg.tap(other[0]["x"], other[0]["y"], wait=1.2)
            continue
        hv, mv = _num(h["t"]), _num(m["t"])
        if hv is None or mv is None:
            raise dg.StepError(f"휠 숫자를 못 읽음('{h['t']}', '{m['t']}') → {p}")
        if hv != want_h:
            fwd = ((want_h % 12) - (hv % 12)) % 12 <= 6
            nxt = [i for i in hours if (i["y"] > h["y"] + 40) == fwd and abs(i["y"] - h["y"]) > 40]
            if not nxt:
                raise dg.StepError(f"시 휠 이동 실패 → {p}")
            dg.tap(nxt[0]["x"] if fwd else nxt[-1]["x"], nxt[0]["y"] if fwd else nxt[-1]["y"], wait=1.2)
            continue
        if mv != want_m:
            fwd = want_m > mv
            nxt = [i for i in mins if (i["y"] > m["y"] + 40) == fwd and abs(i["y"] - m["y"]) > 40]
            if not nxt:
                raise dg.StepError(f"분 휠에서 {want_m:02d}분으로 못 감(5·10분 단위인지 확인) → {p}")
            t = nxt[0] if fwd else nxt[-1]
            dg.tap(t["x"], t["y"], wait=1.2)
            continue
        dg.tap_text("확인", region=(2050, 2340), items=items, wait=2)
        return
    raise dg.StepError("시간 휠을 30번 안에 못 맞춤")
