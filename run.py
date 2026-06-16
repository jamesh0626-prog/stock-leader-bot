"""
주도주 스크리너 메인 실행 파일

실행 방법:
  python run.py           # 봇 상시 실행 (권장)
  python run.py --report  # 리포트 즉시 발송 후 종료
  python run.py --test    # API 연결 테스트
"""
import asyncio
import logging
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
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

    try:
        logger.info("섹터/주도주 스캔 중...")
        scan_result = scan_new_leaders()
        await send_message(format_sector_report(scan_result))

        for ticker in scan_result.get("new_entries", []):
            data = scan_result["candidates"].get(ticker, {})
            if data:
                await send_message(f"🆕 *{ticker} 신규 진입 분석*\n{explain_new_leader(ticker, data)}")
    except Exception as e:
        logger.error(f"스캔 오류: {e}")
        await send_message(f"⚠️ 섹터 스캔 오류: {e}")

    try:
        logger.info("포트폴리오 분석 중...")
        portfolio_results = analyze_portfolio()
        await send_message(format_portfolio_report(portfolio_results))

        for ticker, data in portfolio_results.items():
            if data.get("status") == "🔴 약화":
                await send_message(f"⚠️ *{ticker} 모멘텀 약화 분석*\n{explain_momentum_weakness(ticker, data)}")
    except Exception as e:
        logger.error(f"포트폴리오 오류: {e}")
        await send_message(f"⚠️ 포트폴리오 분석 오류: {e}")

    await send_message("✅ 리포트 완료. 질문이 있으면 메시지를 보내세요.")
    logger.info("일일 리포트 완료")


async def daily_scheduler():
    """schedule 라이브러리 없이 asyncio로 매일 KST 05:30 리포트 실행"""
    from config import DAILY_REPORT_TIME
    h, m = map(int, DAILY_REPORT_TIME.split(":"))

    while True:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if now >= target:
            import datetime as dt
            target += dt.timedelta(days=1)

        wait = (target - now).total_seconds()
        logger.info(f"다음 리포트까지 {wait/3600:.1f}시간 ({target.strftime('%Y-%m-%d %H:%M')} KST)")
        await asyncio.sleep(wait)
        await run_daily_report()


async def run_test():
    """API 연결 테스트"""
    print("\n=== 연결 테스트 시작 ===")
    try:
        from bot.telegram_handler import send_message
        await send_message("🔧 테스트 메시지 - 연결 성공!")
        print("✅ 텔레그램: 연결 성공")
    except Exception as e:
        print(f"❌ 텔레그램: {e}")

    try:
        from ai.gemini_client import answer_question
        answer = answer_question("안녕하세요, 테스트입니다.", {"test": "true"})
        print(f"✅ Gemini: 연결 성공 ({answer[:30]}...)")
    except Exception as e:
        print(f"❌ Gemini: {e}")

    try:
        from data.market_data import get_relative_strength
        rs = get_relative_strength("NVDA", periods=[21])
        print(f"✅ yfinance: 연결 성공 (NVDA 1M RS: {rs.get('21d')}%)")
    except Exception as e:
        print(f"❌ yfinance: {e}")

    print("=== 테스트 완료 ===\n")


async def main_bot():
    """봇 상시 실행 + 스케줄러 병행"""
    from bot.telegram_handler import build_app, send_message

    await send_message("🤖 *주도주 스크리너 시작*\n질문을 입력하거나 일일 리포트를 기다리세요.")

    app = build_app()
    async with app:
        await app.start()
        await app.updater.start_polling()
        logger.info("봇 실행 중...")
        await daily_scheduler()
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
