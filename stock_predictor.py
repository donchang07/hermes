"""
한국 주요 반도체/전자 종목 아침 주가 리포트
- 삼성전자우선주 (005935)
- 삼성전자     (005930)
- SK하이닉스   (000660)
- 삼성전기     (009150)
매일 오전 9시(KST) 텔레그램 발송 / KRX 휴장일 자동 스킵
"""

import os, sys, pathlib
import yfinance as yf
import pandas as pd
from datetime import datetime
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

KST  = pytz.timezone("Asia/Seoul")
XKRX = ec.get_calendar("XKRX")
TICKER_NASDAQ = "^IXIC"

# 종목 정의: (티커, 종목명, 코드)
STOCKS = [
    ("005935.KS", "삼성전자우선주", "005935"),
    ("005930.KS", "삼성전자",     "005930"),
    ("000660.KS", "SK하이닉스",   "000660"),
    ("009150.KS", "삼성전기",     "009150"),
]


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


def predict_price(hist, nq):
    if len(hist) < 22:
        raise ValueError("데이터 부족")
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
    predicted = round(prev_close * (1 + avg_ret * 0.5 + sig_adj + nq * 0.3) / 100) * 100
    return {
        "predicted_price": int(predicted),
        "prev_close": prev_close,
        "ma5": ma5, "ma20": ma20,
        "signal": signal,
    }


def get_actual_price(ticker):
    t  = yf.Ticker(ticker)
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
    return {"current_price": current, "open_price": open_px or current, "prev_close": prev_cls}


def stock_section(name, code, pred, actual):
    pred_px     = pred["predicted_price"]
    open_px     = actual["open_price"]
    prev        = actual["prev_close"]
    diff_pct    = (open_px - pred_px) / pred_px * 100 if pred_px else 0
    vs_prev     = open_px - prev
    vs_prev_pct = vs_prev / prev * 100 if prev else 0
    arrow = "🔴" if vs_prev < 0 else ("🟢" if vs_prev > 0 else "⬜")
    parts = [
        "【" + name + " (" + code + ")】",
        "  🔮 예상: " + f"{pred_px:>10,.0f}" + "원  |  " + pred["signal"],
        "  " + arrow + " 실제: " + f"{open_px:>10,.0f}" + "원  " + f"({vs_prev:+,.0f}원 / {vs_prev_pct:+.2f}%)",
        "  📏 오차: " + f"{diff_pct:+.2f}" + "%   MA5=" + f"{pred['ma5']:,.0f}" + " / MA20=" + f"{pred['ma20']:,.0f}",
    ]
    return "\n".join(parts)


def main():
    now   = datetime.now(KST)
    today = now.date()

    if not is_trading_day(today):
        sys.exit(0)

    nq = nasdaq_overnight_return()

    sections = []
    header = [
        "📊 한국 주요 종목 아침 리포트",
        "📅 " + now.strftime("%Y-%m-%d %H:%M") + " KST",
        "🌐 나스닥 야간: " + f"{nq*100:+.2f}" + "%",
        "═" * 32,
    ]

    for ticker, name, code in STOCKS:
        try:
            hist   = get_history(ticker, days=45)
            pred   = predict_price(hist, nq)
            actual = get_actual_price(ticker)
            sections.append(stock_section(name, code, pred, actual))
        except Exception as exc:
            print(name + " 조회 실패: " + str(exc), file=sys.stderr)
            sections.append("【" + name + " (" + code + ")】\n  ⚠️ 데이터 조회 실패")

    print("\n".join(header) + "\n" + ("\n" + "─" * 32 + "\n").join(sections))


if __name__ == "__main__":
    main()
