"""당근 일정 공유 링크 따오기 + 기록.

흐름: 일정 상세 화면 → 공유(오른쪽 위) → '링크 복사' → (adb로 클립보드를 못 읽으므로)
     모임 전체 채팅방 입력칸(네이티브)에 붙여넣기 → uiautomator로 읽기 → 입력칸 비우기(전송 안 함)
기록: daangn-auto/meetups.jsonl (한 줄 = 일정 하나) + 모임내역.md 끝에 한 줄
"""
import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

import dg

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "..", "meetups.jsonl")
HISTORY_MD = os.path.join(HERE, "..", "..", "모임내역.md")
SHARE_ICON = (880, 176)          # 일정 상세 화면 오른쪽 위 공유 아이콘
ROOM_PREFIX = "나만의 비서 AI 에이전트 구축하기 전체방"
URL_RE = re.compile(r"https://daangn\.com/\S+")


def _dump(name):
    subprocess.run([os.path.join(HERE, "dump.sh"), name], capture_output=True)
    return ET.parse(f"/tmp/dg/{name}.xml").getroot()


def _center(node):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
    return (x1 + x2) // 2, (y1 + y2) // 2


def _editables(root):
    return [n for n in root.iter("node") if n.get("class") == "android.widget.EditText"]


def capture_from_event_page(title):
    """일정 상세 화면에서 시작. 공유 링크 문자열을 돌려준다."""
    p, items = dg.read("event_page")
    if not dg.find(items, title):
        raise dg.StepError(f"일정 상세 화면('{title}')이 아니에요 → {p}")
    dg.tap(*SHARE_ICON, wait=3)
    dg.tap_text("링크 복사", wait=2)
    # 채팅 탭 → 모임 전체방 → 입력칸에 붙여넣기
    for _ in range(6):
        root = _dump("lk_nav")
        tabs = [n for n in root.iter("node") if n.get("content-desc") == "채팅"]
        if tabs:
            break
        dg.back(2)
    else:
        raise dg.StepError("하단 '채팅' 탭을 못 찾음")
    dg.tap(*_center(tabs[0]), wait=3)
    root = _dump("lk_list")
    room = [n for n in root.iter("node") if (n.get("text") or "").startswith(ROOM_PREFIX)]
    if not room:
        raise dg.StepError("채팅 목록에서 모임 전체방을 못 찾음")
    dg.tap(*_center(room[0]), wait=3)
    root = _dump("lk_room")
    eds = _editables(root)
    if len(eds) != 1 or (eds[0].get("text") or ""):
        raise dg.StepError("전체방 입력칸이 비어 있지 않거나 못 찾음(남의 글을 지우지 않으려고 중단)")
    dg.tap(*_center(eds[0]), wait=1.5)
    dg.adb("shell", "input", "keyevent", "279")      # 붙여넣기
    time.sleep(1.5)
    pasted = _editables(_dump("lk_room2"))[0].get("text") or ""
    # 입력칸 비우기 — 전송 버튼은 절대 누르지 않는다
    dg.adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
    for _ in range(len(pasted) + 5):
        dg.adb("shell", "input", "keyevent", "67")
    left = _editables(_dump("lk_room3"))[0].get("text") or ""
    if left:
        raise dg.StepError(f"입력칸을 다 못 비움(직접 지워 주세요): {left!r}")
    m = URL_RE.search(pasted)
    if not m:
        raise dg.StepError(f"붙여넣은 글에 당근 링크가 없음: {pasted!r}")
    return m.group(0)


def record(title, when_iso, url, place=""):
    row = {"title": title, "when": when_iso, "url": url, "place": place,
           "recorded_at": time.strftime("%Y-%m-%d %H:%M")}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    line = f"- {when_iso[:16].replace('T', ' ')} | {title} | {place} | {url}\n"
    md = open(HISTORY_MD, encoding="utf-8").read()
    head = "## 🔗 당근 일정 링크 기록"
    if head not in md:
        md = md.rstrip() + f"\n\n---\n\n{head}\n> 일정을 올리면 자동으로 한 줄씩 추가된다(daangn-auto/meetups.jsonl 과 같은 내용)\n\n"
    md = md.rstrip("\n") + "\n" + line
    open(HISTORY_MD, "w", encoding="utf-8").write(md)
    return row
