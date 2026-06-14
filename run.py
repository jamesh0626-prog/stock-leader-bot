"""
주도주 스크리너 메인 실행 파일

실행 방법:
  python run.py           # 봇 상시 실행 (권장)
  python run.py --report  # 리포트 즉시 발송 후 종료
  python run.py --test    # API 연결 테스트
"""
import asyncio
import logging
import schedule
import time
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/run.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def run_daily_report():
    """일일 리포트 생성 및 텔레그램 전송"""
    logger.info("일일 리포트 시작")
    from bot.telegram_handler import send_message
    from screener.sector_scanner import scan_new_leaders, format_sector_report
    from screener.portfolio_monitor import analyze_portfolio, format_portfolio_report
    from ai.gemini_client import explain_new_leader, explain_momentum_weakness

    await send_message(f"🌅 *{datetime.now().strftime('%Y-%m-%d')} 일일 리포트 시작*")

    # --- 모듈 1: 신규 주도주 스캔 ---
    try:
        logger.info("섹터/주도주 스캔 중...")
        scan_result = scan_new_leaders()
        sector_text = format_sector_report(scan_result)
        await send_message(sector_text)

        # 신규 진입 종목만 Gemini 분석 전송
        for ticker in scan_result.get("new_entries", []):
            data = scan_result["candidates"].get(ticker, {})
            if data:
                logger.info(f"Gemini 분석: {ticker}")
                analysis = explain_new_leader(ticker, data)
                await send_message(f"🆕 *{ticker} 신규 진입 분석*\n{analysis}")
    except Exception as e:
        logger.error(f"스캔 오류: {e}")
        await send_message(f"⚠️ 섹터 스캔 오류: {e}")

    # --- 모듈 2: 보유 종목 모멘텀 ---
    try:
        logger.info("포트폴리오 분석 중...")
        portfolio_results = analyze_portfolio()
        portfolio_text = format_portfolio_report(portfolio_results)
        await send_message(portfolio_text)

        # 약화 종목만 Gemini 분석 전송
        for ticker, data in portfolio_results.items():
            if data.get("status") == "🔴 약화":
                logger.info(f"모멘텀 약화 분석: {ticker}")
                analysis = explain_momentum_weakness(ticker, data)
                await send_message(f"⚠️ *{ticker} 모멘텀 약화 분석*\n{analysis}")
    except Exception as e:
        logger.error(f"포트폴리오 오류: {e}")
        await send_message(f"⚠️ 포트폴리오 분석 오류: {e}")

    await send_message("✅ 리포트 완료. 질문이 있으면 메시지를 보내세요.")
    logger.info("일일 리포트 완료")


def schedule_daily_report():
    """스케줄 등록 — KST 시간을 서버 로컬 시간으로 자동 변환"""
    from config import DAILY_REPORT_TIME
    from zoneinfo import ZoneInfo
    import datetime

    h, m = map(int, DAILY_REPORT_TIME.split(":"))
    kst_dt = datetime.datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=h, minute=m, second=0, microsecond=0)
    local_time = kst_dt.astimezone().strftime("%H:%M")

    def job():
        asyncio.run(run_daily_report())

    schedule.every().day.at(local_time).do(job)
    logger.info(f"일일 리포트 스케줄: 매일 {DAILY_REPORT_TIME} KST → 서버 기준 {local_time}")


async def run_test():
    """API 연결 테스트"""
    print("\n=== 연결 테스트 시작 ===")

    # Telegram 테스트
    try:
        from bot.telegram_handler import send_message
        await send_message("🔧 테스트 메시지 - 연결 성공!")
        print("✅ 텔레그램: 연결 성공")
    except Exception as e:
        print(f"❌ 텔레그램: {e}")

    # Gemini 테스트
    try:
        from ai.gemini_client import answer_question
        answer = answer_question("안녕하세요, 테스트입니다.", {"test": "true"})
        print(f"✅ Gemini: 연결 성공 ({answer[:30]}...)")
    except Exception as e:
        print(f"❌ Gemini: {e}")

    # yfinance 테스트
    try:
        from data.market_data import get_relative_strength
        rs = get_relative_strength("NVDA", periods=[21])
        print(f"✅ yfinance: 연결 성공 (NVDA 1M RS: {rs.get('21d')}%)")
    except Exception as e:
        print(f"❌ yfinance: {e}")

    print("=== 테스트 완료 ===\n")


async def main_bot():
    """봇 상시 실행 + 스케줄 병행"""
    from bot.telegram_handler import build_app, send_message

    schedule_daily_report()
    await send_message("🤖 *주도주 스크리너 시작*\n질문을 입력하거나 일일 리포트를 기다리세요.")

    app = build_app()

    async with app:
        await app.start()
        await app.updater.start_polling()

        logger.info("봇 실행 중... (종료: Ctrl+C)")
        while True:
            schedule.run_pending()
            await asyncio.sleep(30)

        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="리포트 즉시 발송")
    parser.add_argument("--test", action="store_true", help="연결 테스트")
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_test())
    elif args.report:
        asyncio.run(run_daily_report())
    else:
        asyncio.run(main_bot())
