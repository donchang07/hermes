"""
삼성전자우선주 (005935.KS) 예상주가 vs 실제주가 비교 리포트
매일 오전 9시(KST) 텔레그램으로 발송 / KRX 휴장일 자동 스킵
"""

import os, sys, pathlib
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import exchange_calendars as ec
import pytz

# .env 파일 자동 로드
_env_path = pathlib.Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

TICKER_PREF   = "005935.KS"
TICKER_NASDAQ = "^IXIC"
KST        = pytz.timezone("Asia/Seoul")
XKRX       = ec.get_calendar("XKRX")
STOCK_CODE = "005935"


def is_trading_day(check_date=None):
    if check_date is None:
        check_date = datetime.now(KST).date()
    return XKRX.is_session(check_date.isoformat())


def get_history(ticker, days=45):
    t = yf.Ticker(ticker)
    hist = t.history(period=str(days) + "d")
    if not hist.empty:
        hist.index = hist.index.tz_convert(KST)
    return hist


def nasdaq_overnight_return():
    try:
        hist = get_history(TICKER_NASDAQ, days=5)
        if len(hist) >= 2:
            return (float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[-2])) / float(hist["Close"].iloc[-2])
    except Exception:
        pass
    return 0.0


def predict_price(hist):
    if len(hist) < 22:
        raise ValueError("데이터 부족 (최소 22거래일 필요)")
    close      = hist["Close"]
    prev_close = float(close.iloc[-1])
    ma5        = float(close.rolling(5).mean().iloc[-1])
    ma20       = float(close.rolling(20).mean().iloc[-1])
    ma5_prev   = float(close.rolling(5).mean().iloc[-2])
    ma20_prev  = float(close.rolling(20).mean().iloc[-2])
    avg_ret    = float(close.pct_change().dropna().tail(5).mean())
    if ma5 > ma20 and ma5_prev <= ma20_prev:
        signal, sig_adj = "골든크로스 📈", 0.003
    elif ma5 < ma20 and ma5_prev >= ma20_prev:
        signal, sig_adj = "데드크로스 📉", -0.003
    elif ma5 > ma20:
        signal, sig_adj = "상승추세 ↗", 0.001
    else:
        signal, sig_adj = "하락추세 ↘", -0.001
    nq = nasdaq_overnight_return()
    predicted = round(prev_close * (1 + avg_ret * 0.5 + sig_adj + nq * 0.3) / 100) * 100
    reason = (
        "전일종가 " + f"{prev_close:,.0f}" + "원 | "
        + "MA5=" + f"{ma5:,.0f}" + " / MA20=" + f"{ma20:,.0f}" + " (" + signal + ") | "
        + "나스닥 야간 " + f"{nq*100:+.2f}" + "%"
    )
    return {"predicted_price": int(predicted), "prev_close": prev_close,
            "ma5": ma5, "ma20": ma20, "signal": signal,
            "reason": reason, "avg_ret_5d": avg_ret, "nasdaq_ret": nq}


def get_actual_price():
    t  = yf.Ticker(TICKER_PREF)
    fi = t.fast_info
    current  = float(fi.get("lastPrice",     0) or 0)
    open_px  = float(fi.get("open",          0) or 0)
    prev_cls = float(fi.get("previousClose", 0) or 0)
    if open_px == 0:
        try:
            m1 = t.history(period="1d", interval="1m")
            if not m1.empty:
                open_px = float(m1["Open"].iloc[0])
        except Exception:
            pass
    return {"current_price": current, "open_price": open_px or current,
            "prev_close": prev_cls,
            "day_high": float(fi.get("dayHigh", 0) or 0),
            "day_low":  float(fi.get("dayLow",  0) or 0)}


def build_message(pred, actual, now):
    pred_px     = pred["predicted_price"]
    open_px     = actual["open_price"]
    prev        = actual["prev_close"]
    diff        = open_px - pred_px
    diff_pct    = diff / pred_px * 100 if pred_px else 0
    vs_prev     = open_px - prev
    vs_prev_pct = vs_prev / prev * 100 if prev else 0
    arrow = "🔴" if vs_prev < 0 else ("🟢" if vs_prev > 0 else "⬜")
    sep   = "─" * 32
    parts = [
        "📊 삼성전자우선주 (" + STOCK_CODE + ") 아침 리포트",
        "📅 " + now.strftime("%Y-%m-%d %H:%M") + " KST",
        sep,
        "🔮 AI 예상 시초가: " + f"{pred_px:>10,.0f}" + "원",
        "   " + pred["reason"],
        "",
        arrow + " 실제 시초가:     " + f"{open_px:>10,.0f}" + "원",
        "   전일종가 대비: " + f"{vs_prev:+,.0f}" + "원 (" + f"{vs_prev_pct:+.2f}" + "%)",
        "",
        "📏 예측 오차: " + f"{diff:+,.0f}" + "원 (" + f"{diff_pct:+.2f}" + "%)",
        sep,
        "📈 MA5:  " + f"{pred['ma5']:,.0f}" + "원",
        "📉 MA20: " + f"{pred['ma20']:,.0f}" + "원",
        "🎯 추세 신호: " + pred["signal"],
        "🌐 나스닥 야간: " + f"{pred['nasdaq_ret']*100:+.2f}" + "%",
    ]
    return "\n".join(parts)


def main():
    now   = datetime.now(KST)
    today = now.date()
    if not is_trading_day(today):
        # 휴장일: 아무것도 출력하지 않음 (크론잡 텔레그램 발송 없음)
        sys.exit(0)
    try:
        pred = predict_price(get_history(TICKER_PREF, days=45))
    except Exception as exc:
        print("[ERROR] 예상주가 계산 실패: " + str(exc))
        sys.exit(1)
    try:
        actual = get_actual_price()
    except Exception as exc:
        print("[ERROR] 실제주가 조회 실패: " + str(exc))
        sys.exit(1)
    # 메시지를 stdout에 출력 → 크론잡이 텔레그램으로 전달
    print(build_message(pred, actual, now))


if __name__ == "__main__":
    main()
