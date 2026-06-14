import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _to_float(val) -> float | None:
    """pandas Series/scalar 모두 안전하게 float으로 변환"""
    try:
        if val is None:
            return None
        if isinstance(val, (pd.Series, pd.DataFrame)):
            val = val.iloc[0] if len(val) > 0 else None
        return float(val) if val is not None else None
    except Exception:
        return None


def _fix_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance 신버전의 MultiIndex 컬럼을 단일 레벨로 평탄화"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df


def get_price_history(ticker: str, days: int = 200) -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=days + 30)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    df = _fix_columns(df)
    return df.tail(days)


def get_relative_strength(ticker: str, benchmark: str = "SPY", periods: list = [21, 63, 126]) -> dict:
    tickers = [ticker, benchmark]
    end = datetime.today()
    start = end - timedelta(days=200)
    raw = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)

    # 컬럼 구조 정리
    if isinstance(raw.columns, pd.MultiIndex):
        data = raw["Close"]
    else:
        data = raw[["Close"]].rename(columns={"Close": ticker})

    result = {}
    for p in periods:
        try:
            if len(data) < p or ticker not in data.columns or benchmark not in data.columns:
                result[f"{p}d"] = None
                continue
            stock_ret = _to_float((data[ticker].iloc[-1] / data[ticker].iloc[-p] - 1) * 100)
            bench_ret = _to_float((data[benchmark].iloc[-1] / data[benchmark].iloc[-p] - 1) * 100)
            if stock_ret is None or bench_ret is None:
                result[f"{p}d"] = None
            else:
                result[f"{p}d"] = round(stock_ret - bench_ret, 2)
        except Exception:
            result[f"{p}d"] = None
    return result


def get_beta(ticker: str, benchmark: str = "SPY", lookback: int = 90) -> float | None:
    tickers = [ticker, benchmark]
    end = datetime.today()
    start = end - timedelta(days=lookback + 30)
    raw = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)

    if isinstance(raw.columns, pd.MultiIndex):
        data = raw["Close"]
    else:
        return None

    if len(data) < 20 or ticker not in data.columns or benchmark not in data.columns:
        return None

    returns = data.pct_change().dropna().tail(lookback)
    cov = _to_float(returns[ticker].cov(returns[benchmark]))
    var = _to_float(returns[benchmark].var())
    if not cov or not var or var == 0:
        return None
    return round(cov / var, 2)


def get_volume_ratio(ticker: str, short_period: int = 5, long_period: int = 20) -> float | None:
    df = get_price_history(ticker, days=60)
    if df.empty or "Volume" not in df.columns:
        return None
    recent_vol = _to_float(df["Volume"].tail(short_period).mean())
    avg_vol = _to_float(df["Volume"].tail(long_period).mean())
    if not avg_vol or avg_vol == 0:
        return None
    return round(recent_vol / avg_vol, 2)


def get_ma_position(ticker: str) -> dict:
    df = get_price_history(ticker, days=120)
    if df.empty or "Close" not in df.columns:
        return {}

    close = df["Close"]
    current = _to_float(close.iloc[-1])
    ma21 = _to_float(close.tail(21).mean())
    ma50 = _to_float(close.tail(50).mean())

    if current is None or ma21 is None or ma50 is None:
        return {}

    return {
        "current": round(current, 2),
        "ma21": round(ma21, 2),
        "ma50": round(ma50, 2),
        "above_ma21": bool(current > ma21),
        "above_ma50": bool(current > ma50),
        "pct_from_ma21": round((current / ma21 - 1) * 100, 2),
        "pct_from_ma50": round((current / ma50 - 1) * 100, 2),
    }


def is_near_52w_high(ticker: str, threshold_pct: float = 5.0) -> bool:
    df = get_price_history(ticker, days=252)
    if df.empty or "Close" not in df.columns:
        return False
    high_52w = _to_float(df["Close"].max())
    current = _to_float(df["Close"].iloc[-1])
    if high_52w is None or current is None or high_52w == 0:
        return False
    return bool((high_52w - current) / high_52w * 100 <= threshold_pct)


def get_sector_rs(sector_etfs: dict, benchmark: str = "SPY", period: int = 63) -> dict:
    scores = {}
    for etf, name in sector_etfs.items():
        rs = get_relative_strength(etf, benchmark, periods=[period])
        scores[etf] = {"name": name, "rs": rs.get(f"{period}d")}
    return dict(sorted(scores.items(), key=lambda x: x[1]["rs"] or -999, reverse=True))


def get_stocks_in_sector(sector_etf: str, top_n: int = 20) -> list:
    holdings_map = {
        "XLK": ["AAPL", "NVDA", "MSFT", "AVGO", "ORCL", "CRM", "AMD", "INTC", "QCOM", "TXN",
                 "NOW", "AMAT", "MU", "LRCX", "KLAC", "ADI", "MRVL", "CDNS", "SNPS", "FTNT"],
        "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SPGI",
                 "AXP", "CB", "PGR", "ICE", "COF", "USB", "TFC", "PNC", "AIG", "AFL"],
        "XLE": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HAL",
                 "DVN", "HES", "BKR", "FANG", "APA", "MRO", "NOV", "OKE", "WMB", "KMI"],
        "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "BMY",
                 "AMGN", "SYK", "ISRG", "MDT", "REGN", "VRTX", "ZTS", "CI", "HCA", "CVS"],
        "XLI": ["GE", "RTX", "HON", "CAT", "LMT", "UPS", "ETN", "DE", "BA", "WM",
                 "GD", "NOC", "FDX", "EMR", "ITW", "PH", "CMI", "CARR", "TDG", "PCAR"],
        "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG",
                 "ORLY", "AZO", "GM", "F", "MAR", "HLT", "YUM", "DHI", "LEN", "PHM"],
        "XLP": ["PG", "COST", "KO", "PEP", "WMT", "PM", "MO", "CL", "MDLZ", "GIS",
                 "KMB", "SYY", "KHC", "HSY", "CAG", "K", "HRL", "CPB", "MKC", "CLX"],
        "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "CMCSA", "T", "VZ", "CHTR", "EA",
                 "TTWO", "OMC", "IPG", "TMUS", "FOXA", "LYV", "WBD", "PARA", "NWSA", "NWS"],
        "XLU": ["NEE", "SO", "DUK", "SRE", "AEP", "EXC", "XEL", "WEC", "ES", "ED",
                 "ETR", "FE", "EIX", "AES", "CNP", "NI", "PNW", "AEE", "CMS", "LNT"],
        "XLRE": ["PLD", "AMT", "EQIX", "CCI", "PSA", "O", "WELL", "DLR", "AVB", "EQR",
                 "SPG", "VICI", "IRM", "ARE", "MAA", "UDR", "ESS", "BXP", "KIM", "REG"],
        "XLB": ["LIN", "APD", "SHW", "FCX", "NUE", "NEM", "VMC", "MLM", "IP", "PKG",
                 "ALB", "CF", "MOS", "FMC", "CE", "IFF", "PPG", "EMN", "BLL", "SEE"],
    }
    return holdings_map.get(sector_etf, [])[:top_n]
