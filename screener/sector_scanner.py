import json
import os
from datetime import datetime
from config import SECTOR_ETFS, TOP_SECTORS, VOLUME_SURGE_MULTIPLIER, STATE_FILE
from data.market_data import (
    get_sector_rs, get_stocks_in_sector, get_relative_strength,
    is_near_52w_high, get_volume_ratio, get_ma_position
)


def scan_new_leaders() -> dict:
    """
    신규 주도주 감지
    1. SPY 대비 강한 섹터 상위 N개 선정
    2. 해당 섹터 종목 중 돌파 조건 충족 종목 필터
    3. 전날 목록과 비교해 새로 진입한 종목만 '신규' 표시
    """
    print("[스캔] 섹터 강도 계산 중...")
    sector_scores = get_sector_rs(SECTOR_ETFS, period=63)

    top_sectors = list(sector_scores.items())[:TOP_SECTORS]
    sector_names = [f"{etf}({d['name']})" for etf, d in top_sectors]
    print(f"[스캔] 상위 섹터: {sector_names}")

    candidates = {}
    for etf, sector_info in top_sectors:
        print(f"[스캔] {sector_info['name']} 섹터 종목 스캔 중...")
        stocks = get_stocks_in_sector(etf)
        for ticker in stocks:
            try:
                rs = get_relative_strength(ticker, periods=[21, 63])
                vol_ratio = get_volume_ratio(ticker)
                near_high = is_near_52w_high(ticker)
                ma_pos = get_ma_position(ticker)

                # 돌파 조건: 3가지 이상 충족
                conditions = [
                    rs.get("21d", 0) and rs["21d"] > 5,       # 1개월 SPY 대비 +5% 이상
                    rs.get("63d", 0) and rs["63d"] > 10,      # 3개월 SPY 대비 +10% 이상
                    vol_ratio and vol_ratio >= VOLUME_SURGE_MULTIPLIER,  # 거래량 급증
                    near_high,                                  # 52주 고점 근처
                    ma_pos.get("above_ma21") and ma_pos.get("above_ma50"),  # MA 위
                ]
                score = sum(bool(c) for c in conditions)

                if score >= 3:
                    candidates[ticker] = {
                        "sector": sector_info["name"],
                        "sector_etf": etf,
                        "sector_rs_63d": sector_info["rs"],
                        "rs_21d": rs.get("21d"),
                        "rs_63d": rs.get("63d"),
                        "volume_ratio": vol_ratio,
                        "near_52w_high": near_high,
                        "above_ma21": ma_pos.get("above_ma21"),
                        "above_ma50": ma_pos.get("above_ma50"),
                        "score": score,
                        "first_seen": datetime.now().strftime("%Y-%m-%d"),
                    }
            except Exception as e:
                print(f"  [{ticker}] 오류: {e}")
                continue

    # 이전 상태 로드 및 신규 여부 표시
    previous = _load_state()
    new_entries = {t for t in candidates if t not in previous}
    exits = {t for t in previous if t not in candidates}

    for ticker in candidates:
        candidates[ticker]["is_new"] = ticker in new_entries
        if ticker in previous:
            candidates[ticker]["days_on_list"] = (
                datetime.now() - datetime.strptime(previous[ticker].get("first_seen", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
            ).days + 1
        else:
            candidates[ticker]["days_on_list"] = 1

    _save_state(candidates)

    return {
        "sector_ranking": {etf: d for etf, d in sector_scores.items()},
        "top_sectors": top_sectors,
        "candidates": candidates,
        "new_entries": list(new_entries),
        "exits": list(exits),
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(candidates: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)


def format_sector_report(result: dict) -> str:
    lines = ["📊 *섹터 강도 현황 (SPY 대비 3개월)*\n"]
    for etf, d in list(result["sector_ranking"].items())[:6]:
        rs = d["rs"]
        bar = "🟢" if rs and rs > 5 else ("🟡" if rs and rs > 0 else "🔴")
        lines.append(f"{bar} {d['name']} ({etf}): {rs:+.1f}%" if rs else f"⬜ {d['name']} ({etf}): -")

    lines.append("\n🔍 *주도주 후보*\n")
    candidates = result["candidates"]
    if not candidates:
        lines.append("현재 조건 충족 종목 없음")
    else:
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)
        for ticker, d in sorted_candidates[:10]:
            new_tag = " 🆕" if d.get("is_new") else f" ({d.get('days_on_list', 1)}일째)"
            lines.append(
                f"*{ticker}*{new_tag} [{d['sector']}]\n"
                f"  1M: {d['rs_21d']:+.1f}% | 3M: {d['rs_63d']:+.1f}% | 거래량: {d['volume_ratio']:.1f}x"
            )

    if result["exits"]:
        lines.append(f"\n⚠️ 목록 이탈: {', '.join(result['exits'])}")

    return "\n".join(lines)
