# 세팅 가이드

## 1단계: 패키지 설치

```
pip install -r requirements.txt
```

## 2단계: 텔레그램 봇 생성

1. 텔레그램에서 @BotFather 검색
2. /newbot 입력 → 봇 이름 설정
3. 발급받은 **토큰** 복사

4. 본인 채팅 ID 확인:
   - @userinfobot 에 아무 메시지 보내면 ID 알려줌

## 3단계: Gemini API 키 발급

1. https://aistudio.google.com 접속
2. "Get API key" → 키 복사
3. 무료 플랜: 하루 1,500 요청 (충분)

## 4단계: .env 파일 생성

```
# .env.example을 복사해서 .env 로 저장 후 값 입력
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=123456789
GEMINI_API_KEY=AIzaSy...
```

## 5단계: 보유 종목 입력

config.py 파일에서 PORTFOLIO 딕셔너리 수정:
```python
PORTFOLIO = {
    "NVDA": "AI 반도체",
    "TSLA": "전기차/AI",
    # 본인 종목 추가
}
```

## 6단계: 실행

```bash
# 연결 테스트 먼저
python run.py --test

# 리포트 즉시 발송 (테스트용)
python run.py --report

# 봇 상시 실행 (매일 05:30 KST 자동 리포트)
python run.py
```

## 7단계: Windows 시작 시 자동 실행 (선택)

1. Win+R → shell:startup
2. startup 폴더에 .bat 파일 생성:

```bat
@echo off
cd "C:\Users\james\Desktop\구글 드라이브\AI 코딩\Investment"
python run.py
```

## 텔레그램 질문 예시

봇이 실행 중이면 언제든 메시지로 질문 가능:

- "NVDA 지금 모멘텀 어때?"
- "내 포트폴리오에서 가장 강한 종목은?"
- "반도체 섹터 지금 어때?"
- "TSLA 50일선 지금 어디야?"
- "신규 주도주 후보 있어?"
