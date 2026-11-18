#!/bin/bash
# 사용: dump.sh <이름>  → /tmp/dg/<이름>.xml, .png, .txt(보이는 글자·눌리는 요소 요약)
S=${DG_SERIAL:-R3CY308BW0Y}; N=${1:-screen}; O=/tmp/dg
adb -s $S shell uiautomator dump /sdcard/dg.xml >/dev/null 2>&1
adb -s $S pull /sdcard/dg.xml $O/$N.xml >/dev/null 2>&1
adb -s $S exec-out screencap -p > $O/$N.png
python3 - "$O/$N.xml" > $O/$N.txt <<'PY'
import sys,re,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot()
for n in r.iter('node'):
    t=n.get('text') or ''; d=n.get('content-desc') or ''; rid=(n.get('resource-id') or '').split('/')[-1]
    if t or d or n.get('clickable')=='true':
        if not (t or d or rid): continue
        print(f"{'C' if n.get('clickable')=='true' else ' '} {n.get('bounds'):24} {rid[:28]:28} {t[:40]!r} {d[:40]!r}")
PY
echo "$O/$N.txt ($(wc -l < $O/$N.txt) 줄)"
