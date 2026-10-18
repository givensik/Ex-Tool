#!/usr/bin/env python3
"""
track_blank_records.py
- Monitors newly surfaced blank-name records across Food Safety Korea channels:
  1) Web Detail Popup (bsnInfoDetail.do via live production API)
  2) Official OpenAPI I2500
- Records precise timestamps (KST) to identify exact batch update times.
"""

import urllib.request
import json
import time
import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "blank_records_latency.jsonl")
SUMMARY_FILE = os.path.join(LOG_DIR, "latency_summary.txt")

TARGETS = [
    {
        "district": "종로구",
        "industry": "일반음식점",
        "license_no": "20260040717",
        "ledger_no": "2026001000413410",
        "permit_date": "2026-10-16",
        "first_detected": "2026-10-17 20:00 KST"
    },
    {
        "district": "강북구",
        "industry": "일반음식점",
        "license_no": "20260076724",
        "ledger_no": "2026001000413409",
        "permit_date": "2026-10-16",
        "first_detected": "2026-10-17 20:00 KST"
    },
    {
        "district": "강서구",
        "industry": "즉석판매제조가공업",
        "license_no": "20260109491",
        "ledger_no": "2026001000413408",
        "permit_date": "2026-10-16",
        "first_detected": "2026-10-17 20:00 KST"
    },
    {
        "district": "강남구",
        "industry": "유통전문판매업",
        "license_no": "20260147386",
        "ledger_no": "2026001000413407",
        "permit_date": "2026-10-16",
        "first_detected": "2026-10-17 20:00 KST"
    }
]

def check_i2500(lcns_no):
    url = f"http://openapi.foodsafetykorea.go.kr/api/sample/I2500/json/1/1/LCNS_NO={lcns_no}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            rows = data.get("I2500", {}).get("row", [])
            if rows:
                bssh = rows[0].get("BSSH_NM", "").strip()
                addr = rows[0].get("ADDR", "").strip()
                return {"success": True, "bssh_nm": bssh, "addr": addr}
            code = data.get("I2500", {}).get("RESULT", {}).get("CODE", "")
            return {"success": True, "bssh_nm": "", "addr": "", "code": code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def check_web_ledger(ledger_no):
    url = f"https://store.givensik.space/api/ledger?no={ledger_no}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data.get("success"):
                d = data.get("data", {})
                raw_name = d.get("raw_store_name", "").strip()
                addr = d.get("address", "").strip()
                is_pending = data.get("is_pending_name", True)
                return {"success": True, "bssh_nm": raw_name, "addr": addr, "is_pending": is_pending}
            return {"success": False, "error": data.get("error", "unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_check_cycle():
    now_kst = datetime.now(KST)
    timestamp_str = now_kst.strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"\n==========================================")
    print(f"[{timestamp_str}] Checking 4 target records...")

    any_updated = False
    for t in TARGETS:
        lcns = t["license_no"]
        ledg = t["ledger_no"]
        dist = t["district"]
        ind = t["industry"]

        i2500_res = check_i2500(lcns)
        web_res = check_web_ledger(ledg)

        bssh_i2500 = i2500_res.get("bssh_nm", "")
        bssh_web = web_res.get("bssh_nm", "")

        log_entry = {
            "timestamp": timestamp_str,
            "district": dist,
            "industry": ind,
            "license_no": lcns,
            "ledger_no": ledg,
            "i2500": {
                "bssh_nm": bssh_i2500,
                "is_blank": bssh_i2500 == "",
                "status": i2500_res
            },
            "web_detail": {
                "bssh_nm": bssh_web,
                "is_blank": bssh_web == "",
                "status": web_res
            }
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        print(f"[{dist} {ind} ({lcns})] I2500: '{bssh_i2500 or '(공란)'}' | Web: '{bssh_web or '(공란)'}'")

        if bssh_i2500 or bssh_web:
            any_updated = True
            alert_msg = f"🎉 [UPDATE DETECTED!] {dist} {ind} ({lcns}) 상호명 반영 확인!\n" \
                        f"   - 시각: {timestamp_str}\n" \
                        f"   - I2500 상호: {bssh_i2500}\n" \
                        f"   - Web 상세 상호: {bssh_web}\n"
            print(alert_msg)
            with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
                sf.write(alert_msg + "\n")

    if not any_updated:
        print("-> 4건 모두 아직 상호명 반영 대기중 (공란 유지)")

if __name__ == "__main__":
    import sys
    loop_interval = 0
    if len(sys.argv) > 1 and sys.argv[1] == "--loop":
        loop_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 600

    if loop_interval > 0:
        print(f"🚀 Starting continuous tracking daemon (interval: {loop_interval}s)...")
        while True:
            try:
                run_check_cycle()
            except Exception as e:
                print(f"Error in cycle: {e}")
            time.sleep(loop_interval)
    else:
        run_check_cycle()
