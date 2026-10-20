#!/usr/bin/env python3
"""
scripts/monitor_weekday_evening.py
- 평일 저녁(18:00~20:30) 식약처 신규 인허가 레코드의 공란(빈칸) 발생 여부 실데이터 검증 스크립트
- 실행 방법:
  1) 1회성 즉시 점검: python3 scripts/monitor_weekday_evening.py
  2) 특정 시점(18:00, 19:00, 20:00, 20:30) 자동 체크
"""

import urllib.request
import urllib.parse
import http.cookiejar
import ssl
import re
import json
import os
import sys
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "weekday_evening_test.jsonl")

def get_session():
    ctx = ssl._create_unverified_context()
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), urllib.request.HTTPCookieProcessor(cj))
    headers = {"User-Agent": "Mozilla/5.0"}
    r = opener.open(urllib.request.Request("https://www.foodsafetykorea.go.kr/portal/specialinfo/searchInfoCompany.do", headers=headers), timeout=15)
    html = r.read().decode("utf-8", errors="ignore")
    callPage = re.search(r'id=[\"\']callPage[\"\']\s+value=[\"\']([^\"\']+)[\"\']', html).group(1)
    ck = http.cookiejar.Cookie(0, 'callPage', callPage, None, False, 'www.foodsafetykorea.go.kr', True, False, '/', True, False, None, True, None, None, {'HttpOnly': None}, False)
    cj.set_cookie(ck)
    headers.update({"Referer": "https://www.foodsafetykorea.go.kr/portal/specialinfo/searchInfoCompany.do"})
    return opener, headers, callPage

def check_evening_status():
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"[{now_kst}] 평일 저녁 식약처 전산망 공란(빈칸) 실시간 점검 시작...")
    
    try:
        opener, headers, callPage = get_session()
    except Exception as e:
        print(f"❌ 식약처 세션 연결 실패: {e}")
        return

    # 1. 서울 대시보드 API 최신 상태 체크
    try:
        req = urllib.request.Request("https://store.givensik.space/api/businesses?sido=11&page=1&size=20", headers={"User-Agent": "Mozilla/5.0"})
        res = json.loads(opener.open(req, timeout=10).read().decode("utf-8"))
        items = res.get("data", [])
        pending = [i for i in items if i.get("is_pending_name")]
        max_ledger = res.get("max_ledger_no", "N/A")
        print(f"  • 대시보드 최고 대장번호: {max_ledger}")
        print(f"  • 서울 최신 20건 중 공란(상호 반영 대기) 매장: {len(pending)}건")
        for p in pending:
            print(f"    🚨 [서울 공란 발견] 인허가번호: {p.get('license_no')} | 대장: {p.get('ledger_no')} | 업종: {p.get('industry')}")
    except Exception as e:
        print(f"  • 대시보드 API 조회 오류: {e}")

    # 2. 전국 실시간 최신 대장번호 구간 (끝지점 전후 20건) 전수 파싱
    print("  • 전국 실시간 최신 대장번호 전수 파싱 중...")
    # 탐색 시작 지점
    base_num = int(max_ledger) if max_ledger.isdigit() else 2026001000416790
    blanks_found = []
    total_scanned = 0
    current_max = base_num

    for num in range(base_num - 5, base_num + 30):
        url = f"https://www.foodsafetykorea.go.kr/potalPopup/fooddanger/bsnInfoDetail.do?bsnLcnsLedgNo={num}&callPage={callPage}"
        try:
            html = opener.open(urllib.request.Request(url, headers=headers), timeout=5).read().decode("utf-8", errors="ignore")
            pairs = {re.sub(r'<[^>]+>', '', th).strip(): re.sub(r'<[^>]+>', '', td).strip()
                     for th, td in re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL)[:6]}
            if pairs:
                current_max = num
                total_scanned += 1
                bssh = pairs.get("업체명", "").strip()
                addr = pairs.get("소재지", "").strip()
                lcns = pairs.get("인허가번호", "").strip()
                induty = pairs.get("영업 인허가 종류", "").strip()
                prms = pairs.get("인허가일자", "").strip()
                
                # 빈칸 여부 확인
                if not bssh or not addr:
                    blanks_found.append({
                        "ledger_no": str(num),
                        "license_no": lcns,
                        "industry": induty,
                        "permit_date": prms,
                        "bssh_nm": bssh,
                        "addr": addr
                    })
                    print(f"    🚨 [전국 공란 발견!] 대장: {num} | 인허가: {lcns} | 업종: {induty} | 상호: '{bssh}' | 주소: '{addr}'")
            else:
                # 미생성 번호 도달
                break
        except Exception:
            pass

    # 결과 로그 파일에 기록
    log_entry = {
        "timestamp": now_kst,
        "scanned_count": total_scanned,
        "current_max_ledger": current_max,
        "blanks_count": len(blanks_found),
        "blanks": blanks_found
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print("-" * 65)
    if blanks_found:
        print(f"👉 결과: 공란(빈칸) 레코드 {len(blanks_found)}건 발견! (평일 저녁에도 빈칸 발생 팩트 입증)")
    else:
        print(f"👉 결과: 스캔한 {total_scanned}건 중 공란 레코드 0건 (현재 시점엔 모두 정상 기재됨)")
    print(f"📄 로그 저장 위치: {LOG_FILE}\n")

if __name__ == "__main__":
    check_evening_status()
