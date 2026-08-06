"""
금융 문서 AI 도우미용 Streamlit 메인 애플리케이션
"""
import streamlit as st
import os
import sys
from pathlib import Path
import logging

# src를 경로에 추가
sys.path.append(str(Path(__file__).parent / "src"))

from src.chunking import FinancialDocumentChunker
from src.embedding import FinancialEmbeddingStore
from src.retriever import FinancialDocumentRetriever
from src.env_loader import load_environment, get_api_key

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="금융상품 약관 AI 도우미",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c5aa0;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """세션 상태 변수 초기화"""
    if 'vectorstore' not in st.session_state:
        st.session_state.vectorstore = None
    if 'retriever' not in st.session_state:
        st.session_state.retriever = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = False
    if 'auto_submit' not in st.session_state:
        st.session_state.auto_submit = False

def setup_api_key():
    """API 키 설정 인터페이스"""
    st.markdown('<div class="section-header">🔑 API 키 설정</div>', unsafe_allow_html=True)
    
    # API 키 설정 상태 확인
    if st.session_state.api_key_set:
        st.success("✅ API 키가 설정되었습니다.")
        
        # 현재 설정된 API 키 정보 (보안을 위해 일부만 표시)
        current_key = os.getenv("UPSTAGE_API_KEY", "")
        if current_key:
            masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
            st.info(f"현재 API 키: `{masked_key}`")
        
        # API 키 재설정 옵션
        if st.button("API 키 재설정", type="secondary"):
            st.session_state.api_key_set = False
            st.rerun()
    else:
        st.error("❌ API 키가 설정되지 않았습니다.")
        
        # API 키 입력
        st.markdown("### API 키 입력")
        api_key_input = st.text_input(
            "Upstage API 키를 입력하세요:",
            type="password",
            placeholder="up_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            help="Upstage Console에서 발급받은 API 키를 입력하세요"
        )
        
        if st.button("API 키 설정", type="primary"):
            if api_key_input:
                # 환경변수에 직접 설정
                os.environ["UPSTAGE_API_KEY"] = api_key_input
                st.session_state.api_key_set = True
                st.success("API 키가 설정되었습니다!")
                st.rerun()
            else:
                st.error("API 키를 입력해주세요.")
        
        # API 키 발급 가이드
        with st.expander("API 키 발급 방법"):
            st.markdown("""
            ### Upstage API 키 발급 방법
            
            1. **Upstage Console 접속**
               - https://console.upstage.ai/ 에 접속
               
            2. **회원가입/로그인**
               - 계정이 없다면 회원가입
               - 기존 계정이 있다면 로그인
               
            3. **API 키 생성**
               - 대시보드에서 "API Keys" 메뉴 선택
               - "Create New Key" 버튼 클릭
               - API 키 복사 (up_로 시작하는 긴 문자열)
               
            4. **크레딧 확인**
               - 현재 무료 크레딧: $10
               - 사용량에 따라 차감됨
               
            **주의사항:**
            - API 키는 안전하게 보관하세요
            - 공개 저장소에 업로드하지 마세요
            - 크레딧이 부족하면 API 호출이 실패할 수 있습니다
            """)

def load_environment_config():
    """환경 설정 로드 (기존 함수 유지)"""
    # 이 함수는 setup_api_key로 대체됨
    pass

def upload_and_process_pdf():
    """PDF 업로드 및 처리"""
    st.markdown('<div class="section-header">📄 PDF 문서 업로드</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "금융상품 약관 PDF 파일을 업로드하세요:",
        type=['pdf'],
        help="PDF 파일만 업로드 가능합니다."
    )
    
    if uploaded_file is not None:
        # 업로드된 파일 저장
        upload_dir = Path("data/pdfs")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"파일이 업로드되었습니다: {uploaded_file.name}")
        
        # PDF 처리
        if st.button("PDF 처리 및 벡터화", type="primary"):
            try:
                with st.spinner("PDF를 처리하고 있습니다..."):
                    # 청커 초기화
                    chunker = FinancialDocumentChunker(chunk_size=1000, chunk_overlap=200)
                    
                    # PDF 처리
                    chunks = chunker.process_pdf(str(file_path))
                    
                    # 임베딩 스토어 초기화
                    vectorstore = FinancialEmbeddingStore(
                        persist_directory="./vectordb",
                        embedding_model="solar-embedding-1-large-passage"
                    )
                    
                    # 벡터 스토어에 문서 추가
                    metadata = {
                        "source": uploaded_file.name,
                        "document_type": "financial_terms"
                    }
                    vectorstore.add_documents(chunks, metadata)
                    
                    # 세션 상태에 저장
                    st.session_state.vectorstore = vectorstore
                    
                    # 검색기 초기화
                    retriever = FinancialDocumentRetriever(vectorstore)
                    st.session_state.retriever = retriever
                    
                    st.success(f"PDF 처리가 완료되었습니다! {len(chunks)}개의 청크가 생성되었습니다.")
                    
            except Exception as e:
                st.error(f"PDF 처리 중 오류가 발생했습니다: {str(e)}")
                logger.error(f"PDF processing error: {str(e)}")

def load_existing_vectorstore():
    """기존 벡터 스토어 로드"""
    st.markdown('<div class="section-header">📚 기존 문서 로드</div>', unsafe_allow_html=True)
    
    if st.button("기존 벡터 데이터베이스 로드", type="secondary"):
        try:
            with st.spinner("기존 벡터 데이터베이스를 로드하고 있습니다..."):
                # 임베딩 스토어 초기화
                vectorstore = FinancialEmbeddingStore(
                    persist_directory="./vectordb",
                    embedding_model="solar-embedding-1-large-passage"
                )
                
                # 벡터스토어 존재 여부 확인
                if vectorstore.load_existing_vectorstore():
                    # 세션 상태에 저장
                    st.session_state.vectorstore = vectorstore
                    
                    # 검색기 초기화
                    retriever = FinancialDocumentRetriever(vectorstore)
                    st.session_state.retriever = retriever
                    
                    # 컬렉션 정보 가져오기
                    info = vectorstore.get_collection_info()
                    st.success(f"기존 벡터 데이터베이스를 로드했습니다! 총 {info['total_documents']}개의 문서가 있습니다.")
                else:
                    st.warning("기존 벡터 데이터베이스가 없습니다. 먼저 PDF를 업로드해주세요.")
                    
        except Exception as e:
            st.error(f"벡터 데이터베이스 로드 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"Vectorstore loading error: {str(e)}")

def chat_interface():
    """채팅 인터페이스"""
    st.markdown('<div class="section-header">💬 질문하기</div>', unsafe_allow_html=True)
    
    if st.session_state.retriever is None:
        st.warning("먼저 PDF를 업로드하거나 기존 벡터 데이터베이스를 로드해주세요.")
        return
    
    # 예시 질문
    st.markdown("**예시 질문:**")
    sample_questions = [
        "이 카드의 연회비는 얼마인가요?",
        "주요 서비스는 어떻게 되나요?",
        "커피는 할인은 얼마나 되나요?",
        "현금서비스 한도는 얼마인가요?",
        "연체 시 이자율은 어떻게 되나요?"
    ]
    
    for i, question in enumerate(sample_questions):
        if st.button(f"{i+1}. {question}", key=f"sample_{i}"):
            st.session_state.current_question = question
            st.session_state.auto_submit = True
            st.rerun()
    
    # Question input with form for Enter key support
    with st.form("question_form"):
        question = st.text_input(
            "질문을 입력하세요:",
            value=st.session_state.get('current_question', ''),
            placeholder="예: 이 카드의 연회비는 얼마인가요?",
            help="Enter 키를 눌러서도 질문할 수 있습니다."
        )
        
        submit_button = st.form_submit_button("질문하기", type="primary")
    
    if (submit_button or st.session_state.get('auto_submit', False)) and question:
        # 자동 제출 플래그 리셋
        st.session_state.auto_submit = False
        try:
            with st.spinner("답변을 생성하고 있습니다..."):
                # 답변 가져오기
                response = st.session_state.retriever.answer_question(question)
                
                # 답변 표시
                st.markdown("### 답변")
                st.markdown(response['answer'])
                
                # 소스 표시
                if response['sources']:
                    st.markdown("### 참고 문서")
                    for i, source in enumerate(response['sources']):
                        with st.expander(f"참고 문서 {i+1}"):
                            st.markdown(source['content'])
                            st.json(source['metadata'])
                
                # 채팅 기록에 추가
                st.session_state.chat_history.append({
                    'question': question,
                    'answer': response['answer'],
                    'sources': response['sources']
                })
                
        except Exception as e:
            st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"Answer generation error: {str(e)}")

def display_chat_history():
    """채팅 기록 표시"""
    if st.session_state.chat_history:
        st.markdown('<div class="section-header">📝 대화 기록</div>', unsafe_allow_html=True)
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"질문 {len(st.session_state.chat_history) - i}: {chat['question'][:50]}..."):
                st.markdown("**질문:**")
                st.markdown(chat['question'])
                st.markdown("**답변:**")
                st.markdown(chat['answer'])
                
                if chat['sources']:
                    st.markdown("**참고 문서:**")
                    for j, source in enumerate(chat['sources']):
                        st.markdown(f"**참고 {j+1}:** {source['content'][:100]}...")

def main():
    """메인 애플리케이션"""
    st.markdown('<div class="main-header">🏦 금융상품 약관 AI 도우미</div>', unsafe_allow_html=True)
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 환경 설정 자동 로드 제거 - UI에서만 입력받음
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 설정")
        
        if not st.session_state.api_key_set:
            setup_api_key()
        else:
            st.success("✅ 환경 설정이 완료되었습니다.")
            
            # 주요 기능
            tab1, tab2, tab3 = st.tabs(["📄 PDF 업로드", "📚 문서 로드", "💬 질문하기"])
            
            with tab1:
                upload_and_process_pdf()
            
            with tab2:
                load_existing_vectorstore()
            
            with tab3:
                if st.session_state.retriever:
                    st.success("✅ 시스템이 준비되었습니다!")
                else:
                    st.warning("먼저 PDF를 업로드하거나 기존 문서를 로드해주세요.")
    
    # 메인 콘텐츠
    if st.session_state.api_key_set:
        if st.session_state.retriever:
            chat_interface()
            display_chat_history()
        else:
            st.info("👈 사이드바에서 PDF를 업로드하거나 기존 문서를 로드해주세요.")
    else:
        st.info("👈 사이드바에서 API 키를 설정해주세요.")

if __name__ == "__main__":
    main()
