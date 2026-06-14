from config import PORTFOLIO, BETA_THRESHOLD, BETA_LOOKBACK
from data.market_data import get_beta, get_relative_strength, get_volume_ratio, get_ma_position


def analyze_portfolio() -> dict:
    """
    보유 종목 모멘텀 분석
    - 고베타 종목 자동 필터 (BETA_THRESHOLD 이상)
    - 각 종목 모멘텀 점수 및 상태 판정
    """
    results = {}

    for ticker, memo in PORTFOLIO.items():
        print(f"[포트폴리오] {ticker} 분석 중...")
        try:
            beta = get_beta(ticker, lookback=BETA_LOOKBACK)
            rs = get_relative_strength(ticker, periods=[21, 63, 126])
            vol_ratio = get_volume_ratio(ticker)
            ma_pos = get_ma_position(ticker)

            status = _classify_momentum(rs, ma_pos, vol_ratio)

            results[ticker] = {
                "memo": memo,
                "beta": beta,
                "is_momentum_play": beta is not None and beta >= BETA_THRESHOLD,
                "rs_21d": rs.get("21d"),
                "rs_63d": rs.get("63d"),
                "rs_126d": rs.get("126d"),
                "volume_ratio": vol_ratio,
                "above_ma21": ma_pos.get("above_ma21"),
                "above_ma50": ma_pos.get("above_ma50"),
                "pct_from_ma21": ma_pos.get("pct_from_ma21"),
                "pct_from_ma50": ma_pos.get("pct_from_ma50"),
                "current_price": ma_pos.get("current"),
                "status": status,
            }
        except Exception as e:
            results[ticker] = {"memo": memo, "error": str(e), "status": "error"}

    return results


def _classify_momentum(rs: dict, ma_pos: dict, vol_ratio: float) -> str:
    """
    🟢 강함: SPY 대비 아웃퍼폼 + 두 MA 위 + 거래량 증가
    🟡 중립: 혼조 신호
    🔴 약화: SPY 언더퍼폼 + MA 이탈
    """
    rs_21 = rs.get("21d", 0) or 0
    rs_63 = rs.get("63d", 0) or 0
    above_ma21 = ma_pos.get("above_ma21", False)
    above_ma50 = ma_pos.get("above_ma50", False)
    vol_ok = vol_ratio and vol_ratio >= 1.0

    strong_signals = [
        rs_21 > 5,
        rs_63 > 10,
        above_ma21,
        above_ma50,
        vol_ok,
    ]
    weak_signals = [
        rs_21 < -5,
        rs_63 < -10,
        not above_ma21,
        not above_ma50,
    ]

    strong_count = sum(bool(s) for s in strong_signals)
    weak_count = sum(bool(w) for w in weak_signals)

    if strong_count >= 4:
        return "🟢 강함"
    elif weak_count >= 3:
        return "🔴 약화"
    else:
        return "🟡 중립"


def get_portfolio_summary(results: dict) -> dict:
    momentum_plays = {t: d for t, d in results.items() if d.get("is_momentum_play")}
    non_momentum = {t: d for t, d in results.items() if not d.get("is_momentum_play") and "error" not in d}
    errors = {t: d for t, d in results.items() if "error" in d}

    weakening = {t: d for t, d in momentum_plays.items() if d.get("status") == "🔴 약화"}
    strong = {t: d for t, d in momentum_plays.items() if d.get("status") == "🟢 강함"}
    neutral = {t: d for t, d in momentum_plays.items() if d.get("status") == "🟡 중립"}

    return {
        "momentum_plays": momentum_plays,
        "non_momentum": non_momentum,
        "errors": errors,
        "weakening": weakening,
        "strong": strong,
        "neutral": neutral,
        "has_alert": len(weakening) > 0,
    }


def format_portfolio_report(results: dict) -> str:
    summary = get_portfolio_summary(results)
    lines = ["💼 *보유 종목 모멘텀 리포트*\n"]

    momentum_plays = summary["momentum_plays"]
    if not momentum_plays:
        lines.append("모멘텀 추종 종목(베타 1.3+) 없음")
    else:
        lines.append(f"*모멘텀 플레이 종목 (베타 {BETA_THRESHOLD}+)*\n")
        for ticker, d in sorted(momentum_plays.items(), key=lambda x: x[1].get("rs_63d") or -999, reverse=True):
            beta_str = f"β{d['beta']:.1f}" if d.get("beta") else "β?"
            rs21 = f"{d['rs_21d']:+.1f}%" if d.get("rs_21d") is not None else "-"
            rs63 = f"{d['rs_63d']:+.1f}%" if d.get("rs_63d") is not None else "-"
            ma_str = "MA위✓" if d.get("above_ma21") and d.get("above_ma50") else ("MA혼조" if d.get("above_ma50") else "MA아래⚠️")
            lines.append(
                f"{d['status']} *{ticker}* ({beta_str}) - {d['memo']}\n"
                f"  1M: {rs21} | 3M: {rs63} | {ma_str}"
            )

    non_momentum = summary["non_momentum"]
    if non_momentum:
        tickers_str = ", ".join(f"{t}(β{d.get('beta', '?')})" for t, d in non_momentum.items())
        lines.append(f"\n📌 *모멘텀 추종 외 종목*: {tickers_str}")

    if summary["weakening"]:
        lines.append(f"\n⚠️ *모멘텀 약화 경고*: {', '.join(summary['weakening'].keys())}")

    return "\n".join(lines)
