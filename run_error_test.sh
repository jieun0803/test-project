#!/bin/bash

# 에러 처리 테스트 실행 스크립트

echo "🧪 에러 처리 테스트 시작"
echo "================================"

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    exit 1
fi

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 필요한 패키지 설치 확인
echo "📋 패키지 설치 확인 중..."
pip install -q langchain langchain-upstage chromadb streamlit pymupdf pdfplumber spacy transformers torch scikit-learn nltk psutil

# 벡터 데이터베이스 존재 확인
if [ ! -d "vectordb" ]; then
    echo "❌ 벡터 데이터베이스가 없습니다."
    echo "💡 먼저 PDF를 업로드하고 벡터화를 완료해주세요."
    echo "   - 기본 앱: ./run.sh"
    echo "   - 고급 앱: ./run_advanced.sh"
    exit 1
fi

# API 키 확인
if [ -f "config.env" ]; then
    echo "🔑 환경 설정 파일 확인됨"
    source config.env
    if [ -z "$UPSTAGE_API_KEY" ]; then
        echo "❌ UPSTAGE_API_KEY가 설정되지 않았습니다."
        echo "💡 config.env 파일에 UPSTAGE_API_KEY를 설정해주세요."
        exit 1
    fi
else
    echo "❌ config.env 파일이 없습니다."
    echo "💡 config.env 파일을 생성하고 UPSTAGE_API_KEY를 설정해주세요."
    exit 1
fi

echo "✅ 환경 설정 완료"
echo ""

# 에러 처리 테스트 실행
echo "🚀 에러 처리 테스트 실행 중..."
python3 test_error_handling.py

# 테스트 결과에 따른 메시지
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 에러 처리 테스트 완료!"
    echo "✅ 시스템이 다양한 에러 상황을 적절히 처리합니다."
else
    echo ""
    echo "⚠️ 에러 처리 테스트에서 문제가 발견되었습니다."
    echo "💡 에러 처리 코드를 점검해주세요."
fi

echo ""
echo "📋 테스트 완료!"
