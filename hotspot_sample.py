"""구현범위 33행(search_security_hotspots) 검증용 샘플.

SonarCloud Security Hotspot이 탐지되도록 일부러 취약한 패턴을 넣은 파일입니다.
값은 모두 가짜이며, 이 브랜치는 머지하지 않습니다.
"""
import hashlib
import os
import random
import subprocess

import requests

# S2068: 하드코딩된 자격증명
DB_PASSWORD = "FakePassw0rd!ForHotspotTest"
password = "admin1234"


def connect():
    # S2068: 연결 문자열에 비밀번호 포함
    return "postgresql://admin:SuperSecret123@localhost:5432/app"


def weak_hash(data: bytes) -> str:
    # S4790: 취약한 해시 알고리즘
    return hashlib.md5(data).hexdigest()


def fetch_status():
    # S5332: 암호화되지 않은 HTTP 사용
    return requests.get("http://example.com/status", timeout=5)


def make_token() -> int:
    # S2245: 보안 용도에 부적합한 의사난수
    return random.randint(100000, 999999)


def run_cmd(user_input: str):
    # S4721: OS 명령 실행
    os.system("ls " + user_input)
    return subprocess.run("echo " + user_input, shell=True, check=False)
