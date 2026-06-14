from google import genai
from config import GEMINI_API_KEY

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"  # 2026-06 기준 최신 무료 모델


def _generate(prompt: str) -> str:
    response = _client.models.generate_content(model=_MODEL, contents=prompt)
    return response.text.strip()


def explain_new_leader(ticker: str, data: dict) -> str:
    prompt = f"""당신은 미국 주식 전문 애널리스트입니다. 다음 데이터를 바탕으로 {ticker}가 지금 왜 주도주로 부상하고 있는지 한국어로 간결하게 설명하세요 (3-4문장).

- 섹터: {data.get('sector')}
- 섹터 SPY 대비 3개월 초과수익: {data.get('sector_rs_63d', 'N/A')}%
- 종목 SPY 대비 1개월 초과수익: {data.get('rs_21d', 'N/A')}%
- 종목 SPY 대비 3개월 초과수익: {data.get('rs_63d', 'N/A')}%
- 거래량: 20일 평균의 {data.get('volume_ratio', 'N/A')}배
- 52주 신고가 근처: {data.get('near_52w_high')}
- 21일/50일 이평선 위: {data.get('above_ma21')}/{data.get('above_ma50')}

핵심 투자 테마와 모멘텀의 이유를 중심으로 설명하세요."""
    try:
        return _generate(prompt)
    except Exception as e:
        return f"분석 생성 실패: {e}"


def explain_momentum_weakness(ticker: str, data: dict) -> str:
    prompt = f"""당신은 미국 주식 전문 애널리스트입니다. {ticker}의 모멘텀이 약화되고 있는 이유를 한국어로 간결하게 설명하세요 (2-3문장).

- 종목 메모: {data.get('memo')}
- 베타: {data.get('beta')}
- SPY 대비 1개월 초과수익: {data.get('rs_21d', 'N/A')}%
- SPY 대비 3개월 초과수익: {data.get('rs_63d', 'N/A')}%
- 21일 이평선 위치: {'위' if data.get('above_ma21') else '아래'} ({data.get('pct_from_ma21', 'N/A')}%)
- 50일 이평선 위치: {'위' if data.get('above_ma50') else '아래'} ({data.get('pct_from_ma50', 'N/A')}%)
- 거래량: 평균의 {data.get('volume_ratio', 'N/A')}배

보유를 유지해야 할지 재검토가 필요한지 판단 근거도 포함하세요."""
    try:
        return _generate(prompt)
    except Exception as e:
        return f"분석 생성 실패: {e}"


def answer_question(question: str, context: dict) -> str:
    context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
    prompt = f"""당신은 미국 주식 투자 전문가입니다. 아래 시장 데이터를 참고하여 사용자 질문에 한국어로 답변하세요.
투자 철학: 모멘텀이 강한 주도주를 초기에 포착하여 장기 보유하는 스타일.

[현재 시장 데이터]
{context_str}

[사용자 질문]
{question}

데이터에 없는 내용은 솔직하게 모른다고 하고, 있는 데이터만으로 판단하세요. 3-5문장으로 답변하세요."""
    try:
        return _generate(prompt)
    except Exception as e:
        return f"답변 생성 실패: {e}"
