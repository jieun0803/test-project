#!/bin/bash

# 금융상품 약관 AI 도우미 테스트 실행 스크립트

echo "🧪 금융상품 약관 AI 도우미 테스트를 시작합니다..."

# Python 버전 확인
python_version=$(python3 --version 2>&1)
echo "Python 버전: $python_version"

# 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    echo "🔧 가상환경을 활성화합니다..."
    source venv/bin/activate
else
    echo "❌ 가상환경이 없습니다. 먼저 ./run.sh를 실행하여 환경을 설정하세요."
    exit 1
fi

# 환경 파일 확인
if [ ! -f "config.env" ]; then
    echo "⚠️  config.env 파일이 없습니다."
    echo "config.env 파일을 생성하고 UPSTAGE_API_KEY를 설정하세요."
    echo "예시: UPSTAGE_API_KEY=your_actual_api_key_here"
    echo ""
    echo "테스트를 계속하려면 config.env 파일을 설정한 후 다시 실행하세요."
    exit 1
fi

# 필요한 디렉토리 생성
echo "📁 테스트용 디렉토리를 생성합니다..."
mkdir -p data/pdfs
mkdir -p vectordb
mkdir -p src

# 테스트 실행
echo "🚀 자동화된 테스트를 실행합니다..."
echo ""

python3 test_runner.py

echo ""
echo "📊 테스트 완료!"
echo "자세한 결과는 생성된 test_report_*.json 파일을 확인하세요."
