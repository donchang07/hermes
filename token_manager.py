"""
카카오 Access Token 자동 갱신 관리자
Refresh Token으로 Access Token을 갱신하고 .env 파일에 저장합니다.

초기 설정 후 이 파일을 한 번 실행하면 이후 자동 갱신됩니다.
"""

import os, sys, json, pathlib, requests

ENV_FILE   = pathlib.Path(__file__).parent / ".env"
TOKEN_FILE = pathlib.Path(__file__).parent / "kakao_tokens.json"


def load_env():
    """현재 .env 파일 파싱"""
    data = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    return data


def save_env(data: dict):
    """dict를 .env 파일에 저장"""
    lines = []
    for k, v in data.items():
        lines.append(k + "=" + v)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_access_token():
    """Refresh Token으로 새 Access Token 발급"""
    env = load_env()
    rest_api_key   = env.get("KAKAO_REST_API_KEY", "")
    refresh_token  = env.get("KAKAO_REFRESH_TOKEN", "")

    if not rest_api_key or not refresh_token:
        print("[ERROR] KAKAO_REST_API_KEY 또는 KAKAO_REFRESH_TOKEN 이 .env 에 없습니다.")
        print("  → 초기 설정: python token_manager.py init")
        sys.exit(1)

    url  = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type":    "refresh_token",
        "client_id":     rest_api_key,
        "refresh_token": refresh_token,
    }
    resp = requests.post(url, data=data, timeout=10)
    result = resp.json()

    if "access_token" not in result:
        print("[ERROR] 토큰 갱신 실패: " + json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    env["KAKAO_ACCESS_TOKEN"] = result["access_token"]
    if "refresh_token" in result:
        env["KAKAO_REFRESH_TOKEN"] = result["refresh_token"]
        print("[INFO] Refresh Token도 갱신됨")

    save_env(env)
    print("[OK] Access Token 갱신 완료 — .env 파일 업데이트됨")
    return result["access_token"]


def init_with_code(rest_api_key: str, auth_code: str):
    """최초 1회: Authorization Code로 토큰 발급"""
    url  = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type":   "authorization_code",
        "client_id":    rest_api_key,
        "redirect_uri": "https://localhost",
        "code":         auth_code,
    }
    resp   = requests.post(url, data=data, timeout=10)
    result = resp.json()

    if "access_token" not in result:
        print("[ERROR] 초기 토큰 발급 실패: " + json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    env = load_env()
    env["KAKAO_REST_API_KEY"]   = rest_api_key
    env["KAKAO_ACCESS_TOKEN"]   = result["access_token"]
    env["KAKAO_REFRESH_TOKEN"]  = result.get("refresh_token", "")
    save_env(env)
    print("[OK] 초기 토큰 발급 완료! .env 파일에 저장됨")
    print("  Access Token:  " + result["access_token"][:20] + "...")
    print("  Refresh Token: " + result.get("refresh_token", "없음")[:20] + "...")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "init":
        # 사용: python token_manager.py init REST_API_KEY AUTH_CODE
        init_with_code(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2 and sys.argv[1] == "refresh":
        # 사용: python token_manager.py refresh
        refresh_access_token()
    else:
        print("사용법:")
        print("  초기 설정: python token_manager.py init <REST_API_KEY> <AUTH_CODE>")
        print("  토큰 갱신: python token_manager.py refresh")
