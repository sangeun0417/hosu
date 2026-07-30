import os
import urllib.parse
import urllib.request
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY", "").strip()
VALID_ACCESS_CODE = os.getenv("ACCESS_CODE", "4785949").strip()
raw_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
MODEL_NAME = raw_model.replace("models/", "")

# 🎯 네이버 API 키 환경변수 로드
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

client = genai.Client(api_key=api_key) if api_key else None

app = FastAPI(title="호수부동산 AI 백엔드 API - 네이버 실물 이미지 동적 연동")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📸 네이버 이미지 검색 함수 (실물 사진 2장 자동 수집)
def get_naver_real_images(keyword: str):
    # 기본 백업 이미지 (네이버 검색 실패 시 사용)
    default_exterior = "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80"
    default_interior = "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80"

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("⚠️ NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 설정되지 않음 -> 기본 이미지 사용")
        return default_exterior, default_interior

    try:
        encText = urllib.parse.quote(f"{keyword} 아파트 단지 현장")
        url = f"https://openapi.naver.com/v1/search/image?query={encText}&display=5&sort=sim&filter=medium"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            data = json.loads(response_body.decode('utf-8'))
            items = data.get('items', [])
            
            if len(items) >= 2:
                # 검색된 실제 사진 중 1번째, 2번째 고화질 이미지 추출
                img1 = items[0]['link']
                img2 = items[1]['link']
                return img1, img2
            elif len(items) == 1:
                return items[0]['link'], default_interior
    except Exception as e:
        print(f"⚠️ 네이버 이미지 검색 중 오류 발생: {str(e)}")

    return default_exterior, default_interior

class BlogRequest(BaseModel):
    location: str = Field(..., example="강동구 둔촌동")
    topic: str = Field(..., example="올림픽파크포레온 매매 전망 및 입지 분석")
    access_code: str = Field(..., example="4785949")

class BlogResponse(BaseModel):
    success: bool
    title: str
    blog_post: str

@app.post("/api/generate-blog", response_model=BlogResponse)
async def generate_blog(request: BlogRequest):
    if request.access_code != VALID_ACCESS_CODE:
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")

    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key가 서버에 설정되지 않았습니다.")

    # 🎯 [핵심] 입력된 지역과 주제로 네이버에서 진짜 실물 현장 사진 2장 자동 수집!
    search_keyword = f"{request.location} {request.topic.split()[0]}"
    img_exterior, img_interior = get_naver_real_images(search_keyword)

    place_url = "https://map.naver.com/p/entry/place/2004075757"

    prompt = f"""
    너는 현장을 발로 뛰며 깊이 있는 분석을 제공하는 부동산 대표 전문 블로거 '호수부동산'이야.
    주제({request.topic})와 지역({request.location})에 맞게, 읽을거리가 풍부하고 전문성이 느껴지는 고품질 네이버 블로그 원고를 작성해 줘.

    [기본 정보]
    - 작성자: 호수부동산
    - 지역: {request.location}
    - 주제: {request.topic}

    [출력 규칙]
    첫 번째 줄: [제목] 🏠 {request.location} {request.topic} 핵심 현장 분석 및 매수 전략
    (주의: 단어가 연속 중복되지 않게 매끄럽게 작성)

    [본문 작성 양식]
    1. 상단 브리핑 박스:
       <div style="background-color: #f4f9f4; border-left: 5px solid #00c73c; padding: 15px 20px; margin: 15px 0;">
       🏠 <b>[호수부동산 현장 브리핑]</b><br>
       안녕하세요! {request.location} 일대 핵심 매물 분석 전문 <b>호수부동산</b>입니다.<br>
       오늘 리포트에서는 <b>{request.topic}</b>에 대한 생생한 현장 분위기와 실거래 데이터 기반의 향후 전망을 정밀 분석해 드립니다.
       </div>

    2. 첫 번째 소제목 및 현장 분위기 분석:
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 1. 최근 현장 분위기 및 매매 시세 동향</h3>
       ({request.location} 일대의 시세 움직임, 매도자/매수자 심리, 실거래가 추이, 입주장 및 매물 소진 분위기를 최소 4~5문장 이상으로 풍부하고 상세하게 분석해 작성할 것)

       <div style="text-align: center; margin: 20px 0;">
           <img src="{img_exterior}" alt="{request.location} 현장 사진 1" style="width: 100%; max-width: 650px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
       </div>

    3. 두 번째 소제목 및 핵심 입지 분석:
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 2. 핵심 입지 가치 및 주요 프리미엄 요인</h3>
       • 🚆 <b>우수한 교통 인프라</b>: ({request.location} 인근 실제 지하철 노선과 업무지구 접근성을 살려 2문장으로 상세 작성)<br>
       • 🏫 <b>명문 학군 및 생활 환경</b>: ({request.location} 주변 초·중·고 학군 및 편의시설, 공원 환경을 2문장으로 작성)<br>
       • 📈 <b>미래 가치 & 대장주 프리미엄</b>: (주요 개발 호재 및 대단지 프리미엄의 장기 우상향 동력을 2문장으로 작성)

       <div style="text-align: center; margin: 20px 0;">
           <img src="{img_interior}" alt="{request.location} 현장 사진 2" style="width: 100%; max-width: 650px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
       </div>

    4. 세 번째 소제목 및 실전 매수 전략 체크리스트 박스:
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 3. 호수부동산의 실전 타이밍 조언</h3>
       <div style="background-color: #f8f9fa; border: 1px dashed #00c73c; padding: 18px; margin: 15px 0; border-radius: 6px;">
       ✔ <b>실거주 희망자</b>: ({request.location} 실거주자를 위한 타이밍 및 로열동/로열층 매수 조언 2문장)<br>
       ✔ <b>투자 희망자</b>: (전세가율 추이 및 장기 관점 갭투자 전략 조언 2문장)
       </div>

    5. 하단 명함 카드:
       <div style="background-color: #f8f9fa; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; margin-top: 30px;">
       <h4 style="margin: 0 0 10px 0; color: #333;">🏢 호수부동산 전문 상담 및 오시는 길</h4>
       📞 <b>상담문의</b>: 호수부동산 <a href="tel:02-478-5949" style="color: #00c73c; font-weight: bold;">02-478-5949</a> / 대표 채희원 <a href="tel:010-7337-5949" style="color: #00c73c; font-weight: bold;">010-7337-5949</a><br>
       📍 <b>매장위치</b>: <a href="{place_url}" target="_blank" style="color: #00c73c; font-weight: bold;">👉 네이버 지도로 위치 바로보기 (클릭)</a>
       </div>

    6. 해시태그:
       <p style="color: #666; margin-top: 20px;">#호수부동산 #둔촌동역호수부동산 #{request.location}부동산 #{request.location}아파트</p>
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        raw_text = response.text.strip()
        lines = raw_text.split("\n")
        title = lines[0].replace("[제목]", "").replace("제목:", "").strip()
        
        words = title.split()
        clean_words = []
        for w in words:
            if not clean_words or clean_words[-1] != w:
                clean_words.append(w)
        title = " ".join(clean_words)

        content = "\n".join(lines[1:]).strip()

        return BlogResponse(
            success=True,
            title=title if title else f"🏠 [호수부동산] {request.location} {request.topic} 핵심 현장 분석",
            blog_post=content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API 호출 실패 ({MODEL_NAME}): {str(e)}")
