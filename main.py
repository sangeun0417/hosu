import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY", "").strip()

if not api_key:
    # Render 배포 환경변수에서 불러오므로, 서버 구동 시 체크
    print("⚠️ GEMINI_API_KEY 환경변수를 확인해 줘!")

client = genai.Client(api_key=api_key) if api_key else None

app = FastAPI(title="호수부동산 상업용 AI 백엔드 API")

# 🔒 [보안] 모든 프론트엔드 웹 도메인에서의 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BlogRequest(BaseModel):
    location: str = Field(..., example="강동구 둔촌동")
    topic: str = Field(..., example="올림픽파크포레온 매매 전망 및 입지 분석")

class BlogResponse(BaseModel):
    success: bool
    title: str
    blog_post: str

@app.post("/api/generate-blog", response_model=BlogResponse)
async def generate_blog(request: BlogRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key가 서버에 설정되지 않았습니다.")

    place_url = "https://map.naver.com/p/entry/place/2004075757?placePath=%2Fhome%3Fentry%3Dplt%26from%3Dmap%26fromPanelNum%3D1%26additionalHeight%3D76%26timestamp%3D202607310124%26locale%3Dko%26svcName%3Dmap_pcv5&searchType=place&lng=127.1370449&lat=37.5274744&c=15.00,0,0,0,dh"

    prompt = f"""
    너는 현장을 발로 뛰며 깊이 있는 분석을 제공하는 부동산 대표 전문 블로거 '호수부동산'이야.
    네이버 블로그에 그대로 붙여넣었을 때 독자 반응과 가독성이 가장 높은 최고급 원고를 작성해 줘.

    [기본 정보]
    - 작성자: 호수부동산
    - 지역: {request.location}
    - 주제: {request.topic}

    [출력 규칙]
    첫 번째 줄: [제목] 🏠 {request.location} {request.topic} 핵심 현장 분석 및 매수 전략
    (주의: 단어가 연속으로 중복되지 않도록 자연스럽게 다듬을 것)

    [본문 작성 양식]
    1. 상단 브리핑 박스:
       <div style="background-color: #f4f9f4; border-left: 5px solid #00c73c; padding: 15px 20px; margin: 15px 0;">
       🏠 <b>[호수부동산 현장 브리핑]</b><br>
       안녕하세요! {request.location} 일대 핵심 매물 분석 전문 <b>호수부동산</b>입니다.<br>
       오늘 리포트에서는 <b>{request.topic}</b>에 대한 생생한 현장 분위기와 실거래 데이터 기반의 향후 전망을 정밀 분석해 드립니다.
       </div>

    2. 첫 번째 소제목 및 현장 분위기 분석 (3~4문장으로 알차게 작성):
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 1. 최근 현장 분위기 및 매매 시세 동향</h3>
       최근 {request.location} 일대는 입주장 매물 소진이 진행되면서 가격 하방 지지선이 매우 탄탄하게 형성되고 있습니다. 매도자들은 호가를 쉽게 낮추지 않는 분위기이며, 급매물 소진 후 대기 매수자들의 문의가 지속적으로 이어지고 있습니다. 실거주 의무 유예 조치와 맞물려 매수 심리가 안정화되면서 상급지 갈아타기 수요의 유입이 눈에 띄게 증가하는 추세입니다.

       <p style="color: #888; font-size: 14px; text-align: center; margin: 15px 0;">📷 [추천 사진: 단지 전경 및 인근 부동산 현장 사진]</p>

    3. 두 번째 소제목 및 핵심 입지 분석 (이모지 활용 불렛포인트 3개):
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 2. 핵심 입지 가치 및 주요 프리미엄 요인</h3>
       • 🚆 <b>우수한 교통 인프라</b>: 지하철 역세권 입지로 강남(GBD) 및 주요 업무지구로의 출퇴근이 매우 편리합니다.<br>
       • 🏫 <b>명문 학군 및 생활 환경</b>: 단지 인근 초·중·고교 및 학원가 접근성이 뛰어납니다.<br>
       • 📈 <b>미래 가치 & 대장주 프리미엄</b>: 대단지 인프라와 주변 개발 호재가 맞물려 장기 시세 상승 동력이 확실합니다.

    4. 세 번째 소제목 및 실전 매수 전략 체크리스트 박스:
       <h3 style="color: #00c73c; border-bottom: 2px solid #00c73c; padding-bottom: 5px; margin-top: 30px; font-size: 18px;">📌 3. 호수부동산의 실전 타이밍 조언</h3>
       <div style="background-color: #f8f9fa; border: 1px dashed #00c73c; padding: 18px; margin: 15px 0; border-radius: 6px;">
       ✔ <b>실거주 희망자</b>: 로열동·로열층 기준 경쟁력 있는 매물이 나왔을 때 소신 매수 권장<br>
       ✔ <b>투자 희망자</b>: 전세가율 추이를 면밀히 살피며 3~5년 이상 장기 관점 접근 유효
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
            model="gemini-flash-latest",
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
        raise HTTPException(status_code=500, detail=f"Gemini API 호출 실패: {str(e)}")