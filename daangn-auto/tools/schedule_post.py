#!/usr/bin/env python3
"""당근 '나만의 비서 AI 에이전트' 모임에 일정 올리기.

  준비(등록 직전까지):  python3 schedule_post.py prepare --date 2026-12-03 --time 19:00 \
                          [--template "AI 정보공유 함께 해요"] [--title "새 제목"] [--desc-file 설명.txt]
  등록(사람 승인 후):    python3 schedule_post.py submit
  취소(작성 화면 닫기):  python3 schedule_post.py cancel

- 지난 일정 불러오기로 장소·인원·설명·사진을 복사하고 날짜·시간(·제목·설명)만 바꾼다
- prepare 는 마지막 '일정 만들기' 버튼을 절대 누르지 않는다. 마지막 화면 스크린샷을 남기고 끝
- 화면이 예상과 다르면 StepError 로 멈춘다(추측해서 누르지 않음)
"""
import argparse
import fcntl
import datetime as dt
import json
import os
import sys
import time

import dg
import link
import nav
import picker

MOIM = "나만의 비서"
DEFAULT_TEMPLATE = "AI 정보공유 함께 해요"
STATE = os.path.join(dg.SHOT_DIR, "ready.json")


def prepare(a):
    when = dt.datetime.strptime(f"{a.date} {a.time}", "%Y-%m-%d %H:%M")
    if when <= dt.datetime.now():
        raise dg.StepError(f"지난 시각입니다: {when}")
    for f in os.listdir(dg.SHOT_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(dg.SHOT_DIR, f))

    items = nav.open_schedule_list(MOIM)
    title = a.title or a.template
    if not a.allow_dup and nav.upcoming_has(items, title, when):
        raise dg.StepError(f"다가오는 일정에 이미 '{title}' {when.day}일이 있어요(중복 방지). --allow-dup 로 무시")

    nav.start_new_form()
    nav.load_template(a.template)
    try:
        dg.ime_adb()  # 입력기 전환은 팝업을 닫으므로 칸을 열기 전에 먼저
        if a.title:
            nav.set_title(a.template, a.title)
        picker.set_date(when)
        picker.set_time(when)
        summary = nav.verify_summary(when)
        dg.tap_text("다음", region=(2050, 2340), wait=3)
        dg.wait_text("활동에 대한 설명", name="desc_page")
        if a.desc_file:
            nav.set_desc(open(a.desc_file, encoding="utf-8").read().strip())
        desc_shot = dg.shot("desc_check")
        dg.tap_text("다음", region=(2050, 2340), wait=3)
        final, _ = dg.wait_text("옵션을 선택", name="READY_final")
    finally:
        dg.ime_restore()
    json.dump({"at": time.time(), "when": when.isoformat(), "title": title,
               "final": final, "summary": summary, "desc": desc_shot},
              open(STATE, "w"), ensure_ascii=False)
    print(json.dumps({"ok": True, "ready": True, "when": when.strftime("%m/%d %H:%M"),
                      "title": title, "summary_shot": summary, "desc_shot": desc_shot,
                      "final_shot": final}, ensure_ascii=False))


def submit(_):
    lock = open(os.path.join(dg.SHOT_DIR, ".submit.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # 동시에 두 번 실행 방지
    except BlockingIOError:
        raise dg.StepError("이미 등록 중이에요(동시 실행 차단)")
    if not os.path.exists(STATE):
        raise dg.StepError("prepare 기록이 없어요(또는 이미 한 번 눌렀어요). 먼저 prepare 를 실행하세요")
    st = json.load(open(STATE))
    if time.time() - st["at"] > 30 * 60:
        raise dg.StepError("prepare 한 지 30분이 지났어요. 화면을 다시 확인하려면 prepare 부터")
    p, items = dg.read("before_submit")
    if not (dg.find(items, "옵션을 선택") and dg.find(items, "일정 만들기", region=(2050, 2340))):
        raise dg.StepError(f"마지막 옵션 화면이 아니에요 → {p}")
    os.replace(STATE, STATE + ".submitted")   # 누르기 '전에' 기록을 치워 재실행으로 두 번 눌리지 않게
    dg.tap_text("일정 만들기", region=(2050, 2340), items=items, wait=4)
    p, items = dg.wait_text("일정을 생성했어요", timeout=15, name="created")
    if dg.find(items, "건너뛰기"):
        dg.tap_text("건너뛰기", items=items, wait=3)
    p, items = dg.read("posted")
    ok = bool(dg.find(items, st["title"])) and bool(dg.find(items, "모집중"))
    url, link_err = None, None
    if ok:                                   # 올린 직후 상세 화면 → 공유 링크를 따와 기록(사용자 지시 11/19)
        try:
            url = link.capture_from_event_page(st["title"])
            link.record(st["title"], st["when"], url)
        except Exception as e:  # noqa: BLE001 — 등록 자체는 성공이므로 링크 실패만 따로 알린다
            link_err = f"{type(e).__name__}: {e}"
    print(json.dumps({"ok": ok, "posted_shot": p, "title": st["title"], "when": st["when"],
                      "url": url, "link_error": link_err}, ensure_ascii=False))


def relink(a):
    """이미 올린 일정의 링크를 다시 따와 기록: 일정 목록 → 제목 탭 → 공유 링크."""
    items = nav.open_schedule_list(MOIM)
    hits = dg.find(items, a.title)
    if not hits:
        raise dg.StepError(f"일정 목록에 '{a.title}'이 없어요")
    dg.tap(hits[0]["x"], hits[0]["y"], wait=4)
    url = link.capture_from_event_page(a.title)
    row = link.record(a.title, a.when, url)
    print(json.dumps({"ok": True, **row}, ensure_ascii=False))


def cancel(_):
    for _ in range(4):
        _, items = dg.read("cancel")
        if dg.find(items, "다가오는 일정"):
            break
        dg.back(1.5)
    if os.path.exists(STATE):
        os.remove(STATE)
    print(json.dumps({"ok": True, "cancelled": True}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--date", required=True)
    pr.add_argument("--time", required=True)
    pr.add_argument("--template", default=DEFAULT_TEMPLATE)
    pr.add_argument("--title")
    pr.add_argument("--desc-file")
    pr.add_argument("--allow-dup", action="store_true")
    sub.add_parser("submit")
    sub.add_parser("cancel")
    rl = sub.add_parser("link")
    rl.add_argument("--title", required=True)
    rl.add_argument("--when", required=True, help="예: 2026-12-03T19:00")
    a = ap.parse_args()
    try:
        {"prepare": prepare, "submit": submit, "cancel": cancel, "link": relink}[a.cmd](a)
    except Exception as e:  # noqa: BLE001 — 어떤 오류든 멈추고 마지막 화면을 남긴다
        try:
            last = dg.shot("ERROR")
        except Exception:  # noqa: BLE001
            last = None
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "shot": last},
                         ensure_ascii=False))
        sys.exit(1)
    finally:
        dg.ime_restore()


if __name__ == "__main__":
    main()
