#!/bin/bash

# Financial Document AI Assistant 실행 스크립트

echo "🏦 금융상품 약관 AI 도우미를 시작합니다..."

# Python 버전 확인
python_version=$(python3 --version 2>&1)
echo "Python 버전: $python_version"

# 필요한 디렉토리 생성
echo "📁 필요한 디렉토리를 생성합니다..."
mkdir -p data/pdfs
mkdir -p vectordb
mkdir -p src

# 가상환경 확인 및 생성
if [ ! -d "venv" ]; then
    echo "🐍 가상환경을 생성합니다..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "🔧 가상환경을 활성화합니다..."
source venv/bin/activate

# 패키지 설치
echo "📦 필요한 패키지를 설치합니다..."
pip install -r requirements.txt

# 환경 설정 안내
echo "⚠️  환경 설정이 필요합니다:"
echo "config.env 파일에서 UPSTAGE_API_KEY를 설정하세요."
echo "예시: UPSTAGE_API_KEY=your_actual_api_key_here"
echo ""

# Streamlit 앱 실행
echo "🚀 Streamlit 앱을 실행합니다..."
echo "브라우저에서 http://localhost:8501 을 열어주세요."
echo ""

streamlit run app.py
