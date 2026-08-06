"""
고급 RAG 기능을 포함한 Streamlit 메인 애플리케이션
Corrective RAG, Reranking, NER 시스템을 통합한 완전한 금융 문서 AI 도우미
"""
import streamlit as st
import os
import sys
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.chunking import FinancialDocumentChunker
from src.embedding import FinancialEmbeddingStore
from src.retriever import FinancialDocumentRetriever
from src.advanced_rag import AdvancedRAGSystem
from src.env_loader import load_environment, get_api_key

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="고급 금융상품 약관 AI 도우미",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
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
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
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
    if 'basic_retriever' not in st.session_state:
        st.session_state.basic_retriever = None
    if 'advanced_rag' not in st.session_state:
        st.session_state.advanced_rag = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = False
    if 'advanced_features_enabled' not in st.session_state:
        st.session_state.advanced_features_enabled = {
            'corrective_rag': True,
            'reranking': True,
            'ner': True
        }
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
                    
                    # 기본 검색기 초기화
                    basic_retriever = FinancialDocumentRetriever(vectorstore)
                    st.session_state.basic_retriever = basic_retriever
                    
                    # 고급 RAG 시스템 초기화
                    advanced_rag = AdvancedRAGSystem(
                        vectorstore=vectorstore,
                        enable_corrective_rag=st.session_state.advanced_features_enabled['corrective_rag'],
                        enable_reranking=st.session_state.advanced_features_enabled['reranking'],
                        enable_ner=st.session_state.advanced_features_enabled['ner']
                    )
                    st.session_state.advanced_rag = advanced_rag
                    
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
                    
                    # 기본 검색기 초기화
                    basic_retriever = FinancialDocumentRetriever(vectorstore)
                    st.session_state.basic_retriever = basic_retriever
                    
                    # 고급 RAG 시스템 초기화
                    advanced_rag = AdvancedRAGSystem(
                        vectorstore=vectorstore,
                        enable_corrective_rag=st.session_state.advanced_features_enabled['corrective_rag'],
                        enable_reranking=st.session_state.advanced_features_enabled['reranking'],
                        enable_ner=st.session_state.advanced_features_enabled['ner']
                    )
                    st.session_state.advanced_rag = advanced_rag
                    
                    # 컬렉션 정보 가져오기
                    info = vectorstore.get_collection_info()
                    st.success(f"기존 벡터 데이터베이스를 로드했습니다! 총 {info['total_documents']}개의 문서가 있습니다.")
                else:
                    st.warning("기존 벡터 데이터베이스가 없습니다. 먼저 PDF를 업로드해주세요.")
                    
        except Exception as e:
            st.error(f"벡터 데이터베이스 로드 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"Vectorstore loading error: {str(e)}")

def advanced_settings():
    """고급 설정"""
    st.markdown('<div class="section-header">⚙️ 고급 설정</div>', unsafe_allow_html=True)
    
    # 기능 활성화/비활성화
    st.subheader("기능 활성화/비활성화")
    
    corrective_rag = st.checkbox(
        "Corrective RAG 활성화",
        value=st.session_state.advanced_features_enabled['corrective_rag'],
        help="문서 관련성 검증 및 쿼리 재작성 기능"
    )
    
    reranking = st.checkbox(
        "Reranking 활성화",
        value=st.session_state.advanced_features_enabled['reranking'],
        help="문서 재순위화 기능"
    )
    
    ner = st.checkbox(
        "NER (Named Entity Recognition) 활성화",
        value=st.session_state.advanced_features_enabled['ner'],
        help="금융 용어 인식 및 추출 기능"
    )
    
    # 설정 업데이트
    if st.button("설정 적용", type="primary"):
        st.session_state.advanced_features_enabled = {
            'corrective_rag': corrective_rag,
            'reranking': reranking,
            'ner': ner
        }
        
        # 고급 RAG 시스템이 초기화되어 있다면 설정 업데이트
        if st.session_state.advanced_rag:
            st.session_state.advanced_rag.toggle_component("corrective_rag", corrective_rag)
            st.session_state.advanced_rag.toggle_component("reranking", reranking)
            st.session_state.advanced_rag.toggle_component("ner", ner)
        
        st.success("설정이 적용되었습니다!")
    
    # 재순위화 방법 선택
    if reranking:
        st.subheader("재순위화 방법")
        rerank_method = st.selectbox(
            "재순위화 방법을 선택하세요:",
            ["hybrid", "llm", "tfidf", "mmr"],
            help="hybrid: LLM + TF-IDF 조합, llm: LLM만 사용, tfidf: TF-IDF만 사용, mmr: MMR 알고리즘"
        )
        
        if st.session_state.advanced_rag:
            st.session_state.advanced_rag.set_rerank_method(rerank_method)
    
    # 시스템 상태 표시
    if st.session_state.advanced_rag:
        st.subheader("시스템 상태")
        status = st.session_state.advanced_rag.get_system_status()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Corrective RAG", "활성화" if status['corrective_rag_enabled'] else "비활성화")
        with col2:
            st.metric("Reranking", "활성화" if status['reranking_enabled'] else "비활성화")
        with col3:
            st.metric("NER", "활성화" if status['ner_enabled'] else "비활성화")

def chat_interface():
    """채팅 인터페이스"""
    st.markdown('<div class="section-header">💬 고급 질문하기</div>', unsafe_allow_html=True)
    
    if st.session_state.advanced_rag is None:
        st.warning("먼저 PDF를 업로드하거나 기존 벡터 데이터베이스를 로드해주세요.")
        return
    
    # 질문 모드 선택
    question_mode = st.radio(
        "질문 모드를 선택하세요:",
        ["기본 모드", "고급 모드"],
        help="기본 모드: 일반적인 RAG, 고급 모드: Corrective RAG + Reranking + NER"
    )
    
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
    
    # 질문 입력 with form for Enter key support
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
                if question_mode == "고급 모드":
                    # 고급 RAG 처리
                    response = st.session_state.advanced_rag.process_query(question)
                    
                    # 답변 표시
                    st.markdown("### 답변")
                    st.markdown(response['answer'])
                    
                    # 고급 정보 표시
                    if response.get('entities'):
                        st.markdown("### 추출된 금융 엔티티")
                        for entity in response['entities']:
                            st.write(f"• {entity['text']} ({entity['type']})")
                    
                    if response.get('relevance_scores'):
                        st.markdown("### 관련성 점수")
                        avg_score = sum(response['relevance_scores']) / len(response['relevance_scores'])
                        st.metric("평균 관련성 점수", f"{avg_score:.2f}")
                    
                    # 파이프라인 정보
                    if response.get('pipeline_metadata'):
                        with st.expander("처리 파이프라인 정보"):
                            st.json(response['pipeline_metadata'])
                    
                else:
                    # 기본 RAG 처리
                    response = st.session_state.basic_retriever.answer_question(question)
                    
                    # 답변 표시
                    st.markdown("### 답변")
                    st.markdown(response['answer'])
                
                # 소스 표시
                if response.get('sources'):
                    st.markdown("### 참고 문서")
                    for i, source in enumerate(response['sources']):
                        with st.expander(f"참고 문서 {i+1}"):
                            # source가 딕셔너리인 경우와 Document 객체인 경우 모두 처리
                            if hasattr(source, 'page_content'):
                                content = source.page_content
                                metadata = source.metadata
                            elif isinstance(source, dict):
                                content = source.get('content', str(source))
                                metadata = source.get('metadata', {})
                            else:
                                content = str(source)
                                metadata = {}
                            
                            st.markdown(content[:300] + "..." if len(content) > 300 else content)
                            st.json(metadata)
                
                # 채팅 기록에 추가
                st.session_state.chat_history.append({
                    'question': question,
                    'answer': response['answer'],
                    'mode': question_mode,
                    'sources': response.get('sources', []),
                    'entities': response.get('entities', []),
                    'relevance_scores': response.get('relevance_scores', [])
                })
                
        except Exception as e:
            st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
            logger.error(f"Answer generation error: {str(e)}")

def display_chat_history():
    """채팅 기록 표시"""
    if st.session_state.chat_history:
        st.markdown('<div class="section-header">📝 대화 기록</div>', unsafe_allow_html=True)
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"질문 {len(st.session_state.chat_history) - i}: {chat['question'][:50]}... ({chat.get('mode', '기본 모드')})"):
                st.markdown("**질문:**")
                st.markdown(chat['question'])
                st.markdown("**답변:**")
                st.markdown(chat['answer'])
                
                # 고급 모드 정보 표시
                if chat.get('mode') == '고급 모드':
                    if chat.get('entities'):
                        st.markdown("**추출된 엔티티:**")
                        for entity in chat['entities']:
                            st.write(f"• {entity['text']} ({entity['type']})")
                    
                    if chat.get('relevance_scores'):
                        avg_score = sum(chat['relevance_scores']) / len(chat['relevance_scores'])
                        st.metric("평균 관련성 점수", f"{avg_score:.2f}")
                
                if chat.get('sources'):
                    st.markdown("**참고 문서:**")
                    for j, source in enumerate(chat['sources']):
                        # source가 딕셔너리인 경우와 Document 객체인 경우 모두 처리
                        if hasattr(source, 'page_content'):
                            content = source.page_content
                        elif isinstance(source, dict):
                            content = source.get('content', str(source))
                        else:
                            content = str(source)
                        
                        st.markdown(f"**참고 {j+1}:** {content[:100]}...")

def main():
    """메인 애플리케이션"""
    st.markdown('<div class="main-header">🏦 고급 금융상품 약관 AI 도우미</div>', unsafe_allow_html=True)
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 환경 설정 자동 로드 제거 - UI에서만 입력받음
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 설정")
        
        if not st.session_state.api_key_set:
            setup_api_key()
        else:
            st.success("✅ 환경 설정이 완료되었습니다.")
            
            # 주요 기능
            tab1, tab2, tab3, tab4 = st.tabs(["📄 PDF 업로드", "📚 문서 로드", "⚙️ 고급 설정", "💬 질문하기"])
            
            with tab1:
                upload_and_process_pdf()
            
            with tab2:
                load_existing_vectorstore()
            
            with tab3:
                advanced_settings()
            
            with tab4:
                if st.session_state.advanced_rag:
                    st.success("✅ 고급 시스템이 준비되었습니다!")
                else:
                    st.warning("먼저 PDF를 업로드하거나 기존 문서를 로드해주세요.")
    
    # 메인 콘텐츠
    if st.session_state.api_key_set:
        if st.session_state.advanced_rag:
            chat_interface()
            display_chat_history()
        else:
            st.info("👈 사이드바에서 PDF를 업로드하거나 기존 문서를 로드해주세요.")
    else:
        st.info("👈 사이드바에서 API 키를 설정해주세요.")

if __name__ == "__main__":
    main()
