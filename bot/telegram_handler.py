import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from data.market_data import get_relative_strength, get_beta, get_ma_position, get_volume_ratio, get_sector_rs
from ai.gemini_client import answer_question
from screener.portfolio_monitor import analyze_portfolio
from config import PORTFOLIO, SECTOR_ETFS

logger = logging.getLogger(__name__)


async def send_message(text: str, parse_mode: str = ParseMode.MARKDOWN):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    # 4096자 초과 시 분할 전송
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for chunk in chunks:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode=parse_mode)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자 질문 처리"""
    question = update.message.text.strip()
    chat_id = str(update.effective_chat.id)

    if chat_id != str(TELEGRAM_CHAT_ID):
        return

    await update.message.reply_text("⏳ 데이터 조회 중...")

    ctx_data = {}

    # 포트폴리오 전체 데이터를 항상 컨텍스트에 포함
    try:
        results = analyze_portfolio()
        for ticker, d in results.items():
            if "error" in d:
                continue
            ctx_data[f"{ticker}_모멘텀상태"] = d.get("status", "N/A")
            ctx_data[f"{ticker}_베타"] = d.get("beta", "N/A")
            ctx_data[f"{ticker}_1M_SPY대비"] = f"{d.get('rs_21d', 'N/A')}%"
            ctx_data[f"{ticker}_3M_SPY대비"] = f"{d.get('rs_63d', 'N/A')}%"
            ctx_data[f"{ticker}_6M_SPY대비"] = f"{d.get('rs_126d', 'N/A')}%"
            ctx_data[f"{ticker}_21MA위"] = d.get("above_ma21", "N/A")
            ctx_data[f"{ticker}_50MA위"] = d.get("above_ma50", "N/A")
            ctx_data[f"{ticker}_현재가"] = d.get("current_price", "N/A")
    except Exception as e:
        ctx_data["포트폴리오_오류"] = str(e)

    # 포트폴리오 외 종목이 질문에 언급된 경우 추가 조회
    mentioned = _extract_tickers(question)
    extra = [t for t in mentioned if t not in PORTFOLIO]
    for ticker in extra[:3]:
        try:
            rs = get_relative_strength(ticker, periods=[21, 63])
            ma = get_ma_position(ticker)
            ctx_data[f"{ticker}_1M_SPY대비"] = f"{rs.get('21d', 'N/A')}%"
            ctx_data[f"{ticker}_3M_SPY대비"] = f"{rs.get('63d', 'N/A')}%"
            ctx_data[f"{ticker}_21MA위"] = ma.get("above_ma21", "N/A")
            ctx_data[f"{ticker}_50MA위"] = ma.get("above_ma50", "N/A")
        except Exception as e:
            ctx_data[f"{ticker}_오류"] = str(e)

    # 섹터 질문
    if any(k in question for k in ["섹터", "업종"]):
        try:
            sector_rs = get_sector_rs(SECTOR_ETFS)
            for etf, d in list(sector_rs.items())[:5]:
                ctx_data[f"섹터_{d['name']}({etf})_3M"] = f"{d['rs']}%"
        except Exception:
            pass

    answer = answer_question(question, ctx_data)
    await update.message.reply_text(f"🤖 {answer}")


def _extract_tickers(text: str) -> list:
    """텍스트에서 티커 추출 (포트폴리오 종목 + 대문자 단어)"""
    known = set(PORTFOLIO.keys())
    words = text.upper().split()
    found = [w.strip("?!.,") for w in words if w.strip("?!.,") in known]

    # 포트폴리오에 없어도 2-5자 대문자 단어면 티커로 시도
    import re
    extra = re.findall(r'\b[A-Z]{2,5}\b', text.upper())
    combined = list(dict.fromkeys(found + [t for t in extra if t not in {"SPY", "ETF", "MA", "RS"}]))
    return combined[:5]  # 최대 5개


def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    return app
