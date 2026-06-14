from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 보유 종목 목록 (티커: 메모)
# 모멘텀 추종 목적 종목들을 여기에 입력하세요
PORTFOLIO = {
    "NFLX": "스트리밍",
    "GOOGL": "AI/빅테크",
    "RDW": "우주 인프라",
    "AAOI": "광통신/데이터센터",
}

# 섹터 ETF (SPY 대비 강도 비교용)
SECTOR_ETFS = {
    "XLK": "기술",
    "XLF": "금융",
    "XLE": "에너지",
    "XLV": "헬스케어",
    "XLI": "산업재",
    "XLY": "임의소비재",
    "XLP": "필수소비재",
    "XLU": "유틸리티",
    "XLRE": "부동산",
    "XLB": "소재",
    "XLC": "커뮤니케이션",
}

# 고베타 기준 (이 이상이면 모멘텀 플레이로 분류)
BETA_THRESHOLD = 1.3

# 베타 계산 기간 (거래일)
BETA_LOOKBACK = 90

# 신규 주도주 스크리닝: 종목이 속한 섹터 ETF 상위 N개만 스캔
TOP_SECTORS = 3

# 거래량 급증 기준 (20일 평균 대비 배수)
VOLUME_SURGE_MULTIPLIER = 1.5

# 매일 리포트 발송 시각 (한국 시간, 장 마감 후 새벽)
# 미국 동부시간 오후 4시 = 한국시간 다음날 새벽 5시 (EDT 기준)
DAILY_REPORT_TIME = "05:30"  # KST

# 신규 주도주 후보 목록 저장 경로 (전날과 비교용)
STATE_FILE = "data/screener_state.json"
