# Python 버전 업그레이드 가이드

## 개요
이 프로젝트는 Python 3.9.6에서 Python 3.12.12로 성공적으로 업그레이드되었습니다.

## 업그레이드 내용

### 1. Python 버전
- **이전**: Python 3.9.6
- **현재**: Python 3.12.12

### 2. 주요 패키지 업데이트
다음 패키지들이 Python 3.12와 호환되도록 업데이트되었습니다:

| 패키지 | 이전 버전 | 현재 버전 | 변경 사항 |
|--------|----------|----------|-----------|
| numpy | ≥1.24.0 | ≥1.26.0 | Python 3.12 완전 지원 |
| torch | ≥2.0.0 | ≥2.1.0 | Python 3.12 호환성 개선 |
| streamlit | ≥1.28.0 | ≥1.28.0 | 변경 없음 (호환됨) |
| langchain | ≥0.1.0 | ≥0.1.0 | 변경 없음 (호환됨) |
| transformers | ≥4.35.0 | ≥4.35.0 | 변경 없음 (호환됨) |

### 3. 설치된 패키지 버전 (2025년 10월 24일 기준)
```
Python: 3.12.12
Streamlit: 1.50.0
LangChain: 0.3.27
PyTorch: 2.9.0
ChromaDB: 1.2.1
Transformers: 4.46.3
NumPy: 2.3.4
Pandas: 2.3.3
```

## 환경 설정

### 새로운 가상환경 사용법

```bash
# 기존 가상환경 (Python 3.9) - 백업됨
# venv_old_python39/

# 새로운 가상환경 (Python 3.12)
source venv/bin/activate
```

### Python 버전 확인

```bash
python --version
# 출력: Python 3.12.12
```

## 호환성 검증

### 검증된 기능
✅ 모든 커스텀 모듈 임포트  
✅ Streamlit 앱 시작  
✅ LangChain 통합  
✅ PyTorch 및 Transformers  
✅ ChromaDB 벡터 데이터베이스  
✅ PDF 처리 (PyMuPDF, pdfplumber)  

### 코드 변경 사항
- **변경 없음**: 기존 코드는 Python 3.12와 완전히 호환됩니다.
- 모든 타입 힌트 (typing 모듈)가 정상 작동합니다.
- pathlib, logging 등 표준 라이브러리 호환 확인 완료

## 실행 방법

### 1. 기본 앱 실행
```bash
./run.sh
# 또는
source venv/bin/activate
streamlit run app.py
```

### 2. 고급 기능 앱 실행
```bash
./run_advanced.sh
# 또는
source venv/bin/activate
streamlit run advanced_app.py
```

### 3. 테스트 실행
```bash
./run_tests.sh
# 또는
source venv/bin/activate
python test_runner.py
```

## SSL 인증서 이슈 해결

업그레이드 중 macOS에서 SSL 인증서 문제가 발생할 수 있습니다:

### 해결 방법
```bash
# pip 설치 시 --trusted-host 플래그 사용
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org [패키지명]
```

## 주의사항

1. **기존 가상환경 백업**
   - 기존 Python 3.9 가상환경은 `venv_old_python39/`로 백업되었습니다.
   - 필요 시 복원할 수 있습니다.

2. **벡터 데이터베이스**
   - 기존 `vectordb/` 디렉토리는 그대로 사용 가능합니다.
   - ChromaDB가 Python 3.12와 호환됩니다.

3. **API 키**
   - `config.env` 파일의 API 키 설정은 변경 없이 사용됩니다.

## Python 3.12의 주요 개선사항

### 성능 향상
- 전체적인 성능 개선 (Python 3.9 대비 약 10-15% 향상)
- 메모리 사용량 최적화

### 새로운 기능
- 개선된 에러 메시지
- 타입 힌팅 개선 (PEP 692, 695, 698)
- f-string 개선
- 더 나은 디버깅 지원

### 보안
- 최신 보안 패치 적용
- 더 안전한 표준 라이브러리

## 문제 해결

### 가상환경 재생성이 필요한 경우

```bash
# 1. 기존 가상환경 삭제
rm -rf venv

# 2. Python 3.12로 새 가상환경 생성
python3.12 -m venv venv

# 3. 가상환경 활성화
source venv/bin/activate

# 4. 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 패키지 의존성 문제

```bash
# 모든 패키지 재설치
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

## 변경 이력

- **2025-10-24**: Python 3.9.6 → 3.12.12 업그레이드 완료
  - numpy, torch 버전 업데이트
  - 모든 패키지 재설치
  - 호환성 검증 완료

## 연락처

문제가 발생하면 다음을 확인하세요:
1. Python 버전: `python --version`
2. 설치된 패키지: `pip list`
3. 가상환경 활성화 여부: `which python`

