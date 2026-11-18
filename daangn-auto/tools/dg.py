"""당근(S25) 화면 조작 공용 함수 — 스크린샷 + 맥 Vision 글자 인식으로 '글자를 찾아서' 누른다.

안전 원칙
- 누르기 전 매번 당근 앱이 맨 앞인지 확인(아니면 즉시 중단) — 11/18 토스 오탭 사고 재발 방지
- 찾는 글자가 없으면 추측해서 누르지 않고 멈춘다(StepError)
"""
import base64
import json
import os
import subprocess
import time

SERIAL = os.environ.get("DG_SERIAL", "R3CY308BW0Y")
PKG = "com.towneers.www"
HERE = os.path.dirname(os.path.abspath(__file__))
OCR_BIN = os.path.join(HERE, "ocr")
SHOT_DIR = "/tmp/dg/run"
ADB_IME = "com.android.adbkeyboard/.AdbIME"
DEFAULT_IME = "com.samsung.android.honeyboard/.service.HoneyBoardService"
os.makedirs(SHOT_DIR, exist_ok=True)


class StepError(Exception):
    """화면이 예상과 다를 때 — 여기서 멈추고 사람에게 스크린샷을 보여준다."""


def adb(*args, check=True):
    try:
        r = subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        raise StepError(f"adb 응답 없음: {' '.join(args)}")
    if check and r.returncode != 0:
        raise StepError(f"adb 실패: {' '.join(args)} → {r.stderr.strip()}")
    return r.stdout


def foreground():
    out = adb("shell", "dumpsys", "window")
    for line in out.splitlines():
        if "mCurrentFocus" in line:
            return line.strip()
    return ""


def ensure_daangn():
    f = foreground()
    if PKG not in f:
        raise StepError(f"당근이 맨 앞이 아님 → {f}")


_shot_no = [0]


def shot(name=None):
    """스크린샷 저장 후 경로 반환."""
    _shot_no[0] += 1
    path = os.path.join(SHOT_DIR, f"{_shot_no[0]:02d}_{name or 'screen'}.png")
    try:
        data = subprocess.run(["adb", "-s", SERIAL, "exec-out", "screencap", "-p"],
                              capture_output=True, timeout=30).stdout
    except subprocess.TimeoutExpired:
        raise StepError("스크린샷 응답 없음")
    with open(path, "wb") as f:
        f.write(data)
    return path


def ocr(path):
    try:
        out = subprocess.run([OCR_BIN, path], capture_output=True, text=True, timeout=30).stdout
    except subprocess.TimeoutExpired:
        raise StepError("글자 인식 응답 없음")
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def read(name=None):
    p = shot(name)
    return p, ocr(p)


def norm(s):
    """비교용: 공백 제거 + OCR이 헷갈리는 I/l/| 통일(예: 'AI'를 'Al'로 읽음)."""
    return s.replace(" ", "").upper().replace("L", "I").replace("|", "I")


def find(items, text, exact=False, region=None):
    """글자 찾기. region=(y_min, y_max). 여러 개면 위에서부터."""
    t = norm(text)
    hits = []
    for it in items:
        s = norm(it["t"])
        ok = (s == t) if exact else (t in s)
        if not ok:
            continue
        if region and not (region[0] <= it["y"] <= region[1]):
            continue
        hits.append(it)
    return sorted(hits, key=lambda i: i["y"])


def tap(x, y, wait=1.5):
    ensure_daangn()
    adb("shell", "input", "tap", str(int(x)), str(int(y)))
    time.sleep(wait)


def tap_text(text, exact=False, region=None, wait=2.0, pick=0, items=None, name=None):
    if items is None:
        _, items = read(name or f"find_{norm(text)[:8]}")
    hits = find(items, text, exact, region)
    if not hits:
        raise StepError(f"'{text}' 글자를 화면에서 못 찾음")
    h = hits[pick]
    tap(h["x"], h["y"], wait)
    return h


def wait_text(text, timeout=12, exact=False, region=None, name=None):
    end = time.time() + timeout
    while True:
        p, items = read(name or f"wait_{norm(text)[:8]}")
        if find(items, text, exact, region):
            return p, items
        if time.time() > end:
            raise StepError(f"'{text}' 화면이 {timeout}초 안에 안 나옴 (마지막 화면 {p})")
        time.sleep(1.5)


def back(wait=1.5):
    ensure_daangn()
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(wait)


def swipe(x1, y1, x2, y2, ms=400, wait=1.5):
    ensure_daangn()
    adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms))
    time.sleep(wait)


# ---- 한글 입력 (ADBKeyboard) ----
def ime_adb():
    adb("shell", "ime", "set", ADB_IME)
    time.sleep(1.2)


def ime_restore():
    adb("shell", "ime", "set", DEFAULT_IME, check=False)


def type_text(s, clear=False):
    """현재 포커스 칸에 입력. 칸을 누른 뒤 1.5초 이상 지나서 부를 것."""
    ensure_daangn()
    if clear:
        adb("shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT")
        time.sleep(0.8)
        ensure_daangn()
    b64 = base64.b64encode(s.encode("utf-8")).decode()
    adb("shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64)
    time.sleep(1.5)
