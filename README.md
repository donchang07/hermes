# 삼성전자우선주 아침 주가 리포트

매일 오전 9시 KST, 삼성전자우선주(005935)의 AI 예상 시초가와 실제 시초가를 비교해 카카오톡으로 발송합니다.
KRX 휴장일 (공휴일, 주말)에는 자동으로 스킵됩니다.

---

## 파일 구조

- stock_predictor.py  — 메인 스크립트 (예측 + 실제 비교 + 카카오 발송)
- token_manager.py   — 카카오 토큰 초기 발급 및 자동 갱신
- .env               — 환경변수 저장 파일 (직접 생성 필요, git 제외)
- README.md          — 이 파일

---

## 카카오톡 연동 설정 (1회만 필요)

### 1단계: 카카오 앱 생성
1. https://developers.kakao.com 에서 로그인
2. [내 애플리케이션] > [애플리케이션 추가하기]
3. 앱 이름 자유 입력 (예: 삼성주가봇)
4. [앱 설정] > [플랫폼] > Web 플랫폼 추가: https://localhost

### 2단계: 카카오 로그인 + 메시지 권한 활성화
1. [제품 설정] > [카카오 로그인] > 활성화 ON
2. Redirect URI 추가: https://localhost
3. [동의항목] > "카카오톡 메시지 전송" 필수 동의로 설정

### 3단계: Authorization Code 받기
아래 URL을 브라우저에서 열기 (YOUR_REST_API_KEY 교체):

  https://kauth.kakao.com/oauth/authorize?client_id=YOUR_REST_API_KEY&redirect_uri=https://localhost&response_type=code

로그인 후 리다이렉트된 URL에서 code=XXXXX 부분의 코드 복사

### 4단계: 토큰 초기 발급

  cd C:\Users\donch\hermes\samsung-stock-tracker
  python token_manager.py init YOUR_REST_API_KEY YOUR_AUTH_CODE

성공하면 .env 파일에 자동 저장됩니다.

### 5단계: 동작 확인

  python stock_predictor.py

"[OK] 카카오톡 발송 성공" 이 출력되면 완료!

---

## 자동 토큰 갱신

카카오 Access Token은 6시간마다 만료됩니다.
매일 실행되는 stock_predictor.py가 .env의 KAKAO_REFRESH_TOKEN으로 자동 갱신합니다.

수동으로 갱신하려면:
  python token_manager.py refresh

---

## 예측 모델 원리

요소                  | 가중치 | 설명
전일 종가              | 기준   | 베이스라인
최근 5일 평균 등락률   | 50%    | 최근 모멘텀
MA5/MA20 크로스 신호   | 0.1~0.3% | 골든/데드크로스 감지
나스닥 야간 등락률     | 30%    | 글로벌 시장 영향

예측 정확도는 보통 1~3% 오차 범위입니다. 주식 투자 판단에 단독으로 사용하지 마세요.

---

## 크론잡 정보

스케줄: 매주 월~금 오전 9시 KST (cron: 0 0 * * 1-5 UTC)
Job ID: 38088a920499
현황: Hermes 크론잡으로 자동 실행 중
