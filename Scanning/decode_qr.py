import base64
import io
import cv2
from PIL import Image

base64_data = """iVBORw0KGgoAAAANSUhEUgAAAMgAAADIAQAAAACFI5MzAAAEGElEQVR4Xt2YPY60OBCGCzkgoy+A5GuQcSW4QDdcAK5ExjUs+QJN5sDC+5R7NNKu9AVdm6wWofnpd4RNVb0/Hil/uuSfH/xe/21EpA3Nmeczbm1cS9+cZT2kMSK+nHlq+8fhbumbUrbBrWe5jAgP9nvquayF3rdtTfuknMtsRtwyhG+Mt/h5DJ2H+V0gvA5sVEVdKfrbhYUeogduP+G7dVfx7DI+jf/1W52uE/vTz+ff7t3NfI1zuOmI53Fr8MsijuJ/ZsSC9tLk58nOIb3FLW+g567yMSCzFXwetppt96/A7zT+81sCCaAnpj9Y1iWi3KW14GBFpEnf/lF7Gwuy8EgP+4ZwBCa8zyNB3Y2gS5IubuL0E7Y8F6Sd6csBdnes1UWAY7Hcj4tcTJM9HXEa4Gx5JpjZrf0xIScy1dDo15UrhVZCZ2m0L4t6CuogM+ZXK1kLBWM6o3bYgzLJb2XVxd+tY82IdhtGIuP3MnfRoAMTdT7cm9x4qgy1IfI88PtalyjaG58ius65jQfJTAuSgMyLhKWVFukan61gQeaW4KUtKQbFGOpPZfp14CzIfyrZJyiaMNvWgV9GK0FgKmRnAmdK28Uq+8BJGRFQ1j/zg1fGKw29KPjOCriPwflPly9IymPEeP5wzIPFuUXTGkPeOKzXAdUuoc2BAcjeWnaIeWUQ5N6swVAZbkLIIMtzT80UoBl2iV331HwOCyPE97icr+K11i45hragFcdfpLjIFTnv666y2dn4YbECyPl7UefDGm7lOmKSoY1gQ/xZuaEFF9eOSwiQ/s/M9Qm4qd1uWVjqySfLLWOof2hC4qw7G29PkiYRyUmBvRVSc9lQFj9WqN7Lx6sEGBHKErsX8mcc8DTiGVvejo98jrrKNEsbrYI7ycyQLfPTagAj+340EAZJO0HVIFhq0bUh4DiQdcgRKQHPQUfyn9seCoMFObUdzE0WN14nMmxGSdW50p7Qo3oPmzWkoddcWBBHFsVGFRevKz9Kc/cuIEOuwWVhLQmeIkD18sq5jQcgjHhFdBF3RinYtyUJJbELCpL9hs5BP12mOfk51diwImperEkflLpxLDkGtLDEgmS9z4tl4jqc/IOX4zIEBQaHwfz2EUVoi56XxJzdGRD1nGvOMJBxxG6FgmFNNdhZE3fUe+gb/4UCs/oNvfNKTAdECTCNV5HBDt1EpXVB924Q8mLuThqPx7j1y4iFc1LOmBeHSx5NKeO9uINIiLT96/T0Cd1EpUklUohxlJ+ycVUctCOdgdulXPa16evXQiF3XsSD6/4MF2mlR3VY9jWJUbtsQIjDbVCV+Dmpld/txWhvC9HE0x7SZGnjMib9OogWhBmr7tcmMJFxBpPuaKQwI/aEAxEPkkxSmvs1p4MPG75E/Xf835C9cVAh+4a4pDwAAAABJRU5ErkJggg=="""

try:
    # 1. Base64 디코딩
    img_bytes = base64.b64decode(base64_data)
    
    # 2. PIL로 먼저 로드하여 원본 데이터 복호화 (PIL은 libpng 필터 오류에 비교적 관대함)
    pil_img = Image.open(io.BytesIO(img_bytes))
    
    # 3. RGB 모드로 변환하여 규격화된 깨끗한 PNG 파일로 임시 저장
    clean_path = "Scanning/clean_qr.png"
    pil_img.convert("RGB").save(clean_path, "PNG")
    print("✓ PIL을 통해 복원된 표준 PNG 생성 완료.")
    
    # 4. OpenCV로 변환된 안전한 이미지 로드
    img = cv2.imread(clean_path)
    
    # 5. OpenCV QRCodeDetector로 디코딩
    detector = cv2.QRCodeDetector()
    data, bbox, straight_qrcode = detector.detectAndDecode(img)
    
    if data:
        print("\n✅ QR 코드 해독 성공!")
        print("----------------------------------------")
        print(data)
        print("----------------------------------------")
    else:
        print("\n❌ QR 코드를 인식하지 못했거나 내부에 텍스트 데이터가 없습니다.")
        
except Exception as e:
    print(f"\n❌ 에러 발생: {e}")
