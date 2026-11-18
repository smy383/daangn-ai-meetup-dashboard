#!/bin/bash
# 사용: tap.sh X Y  — 당근 앱이 맨 앞일 때만 누른다(다른 앱 오작동 방지)
S=${DG_SERIAL:-R3CY308BW0Y}
F=$(adb -s $S shell dumpsys window | grep -m1 mCurrentFocus)
case "$F" in *com.towneers.www*) adb -s $S shell input tap "$1" "$2";; *) echo "중단: 당근이 맨 앞이 아님 → $F" >&2; exit 1;; esac
