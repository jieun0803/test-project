"""
금융상품 약관 AI 도우미 자동화 테스트 스크립트
모든 기능을 체계적으로 테스트하고 결과를 리포트로 생성
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.embedding import FinancialEmbeddingStore
from src.retriever import FinancialDocumentRetriever
from src.advanced_rag import AdvancedRAGSystem
from src.corrective_rag import CorrectiveRAG
from src.reranker import DocumentReranker
from src.finance_ner import FinancialNER

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestRunner:
    """자동화된 테스트 실행기"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        
        # 테스트 데이터
        self.test_questions = {
            "basic": [
                "이 금융상품의 이자율은 얼마인가요?",
                "수수료는 어떻게 계산되나요?",
                "대출 한도는 얼마인가요?",
                "만기 기간은 얼마나 되나요?",
                "연체 시 이자율은 어떻게 되나요?"
            ],
            "advanced": [
                "이 카드의 이자율과 수수료에 대해 알려주세요",
                "대출 조건과 한도를 자세히 설명해주세요",
                "연체 시 적용되는 이자율과 수수료는 어떻게 되나요?",
                "카드 이용한도와 현금서비스한도는 각각 얼마인가요?",
                "수수료 계산 방법과 연회비는 어떻게 되나요?"
            ],
            "ner": [
                "이자율이 15%인가요?",
                "수수료가 1,000원인가요?",
                "한도가 500만원인가요?",
                "만기가 3년인가요?",
                "연회비는 얼마인가요?"
            ],
            "edge_cases": [
                "이 카드의 색깔은 무엇인가요?",  # 관련성 낮음
                "이자",  # 너무 간단
                "수수료",  # 모호함
                "한도"  # 컨텍스트 부족
            ]
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        logger.info("🧪 테스트 시작")
        
        # 1. 환경 설정 테스트
        self.test_environment_setup()
        
        # 2. 기본 기능 테스트
        self.test_basic_functionality()
        
        # 3. 고급 기능 테스트
        self.test_advanced_functionality()
        
        # 4. 통합 시스템 테스트
        self.test_integrated_system()
        
        # 5. 성능 테스트
        self.test_performance()
        
        # 6. 결과 리포트 생성
        self.generate_report()
        
        return self.test_results
    
    def test_environment_setup(self):
        """환경 설정 테스트"""
        logger.info("🔧 환경 설정 테스트 시작")
        
        test_name = "environment_setup"
        self.test_results[test_name] = {
            "status": "running",
            "start_time": time.time(),
            "details": {}
        }
        
        try:
            # API 키 확인
            api_key = os.getenv("UPSTAGE_API_KEY")
            if not api_key:
                raise ValueError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다")
            
            # 디렉토리 확인
            required_dirs = ["data/pdfs", "vectordb", "src"]
            for dir_path in required_dirs:
                if not Path(dir_path).exists():
                    Path(dir_path).mkdir(parents=True, exist_ok=True)
            
            # 모듈 임포트 테스트
            from src.chunking import FinancialDocumentChunker
            from src.embedding import FinancialEmbeddingStore
            from src.retriever import FinancialDocumentRetriever
            
            self.test_results[test_name]["status"] = "passed"
            self.test_results[test_name]["details"] = {
                "api_key_set": True,
                "directories_created": True,
                "modules_imported": True
            }
            
            logger.info("✅ 환경 설정 테스트 통과")
            
        except Exception as e:
            self.test_results[test_name]["status"] = "failed"
            self.test_results[test_name]["error"] = str(e)
            logger.error(f"❌ 환경 설정 테스트 실패: {str(e)}")
    
    def test_basic_functionality(self):
        """기본 기능 테스트"""
        logger.info("📄 기본 기능 테스트 시작")
        
        test_name = "basic_functionality"
        self.test_results[test_name] = {
            "status": "running",
            "start_time": time.time(),
            "details": {}
        }
        
        try:
            # 벡터스토어 초기화
            vectorstore = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            # 기본 검색기 초기화
            retriever = FinancialDocumentRetriever(vectorstore)
            
            # 기본 질문 테스트
            basic_questions = self.test_questions["basic"]
            results = []
            
            for question in basic_questions:
                start_time = time.time()
                try:
                    response = retriever.answer_question(question)
                    processing_time = time.time() - start_time
                    
                    results.append({
                        "question": question,
                        "answer_length": len(response.get("answer", "")),
                        "num_sources": response.get("num_sources", 0),
                        "processing_time": processing_time,
                        "success": True
                    })
                    
                except Exception as e:
                    results.append({
                        "question": question,
                        "error": str(e),
                        "success": False
                    })
            
            # 결과 분석
            successful_tests = sum(1 for r in results if r.get("success", False))
            avg_processing_time = sum(r.get("processing_time", 0) for r in results if r.get("success")) / max(successful_tests, 1)
            
            self.test_results[test_name]["status"] = "passed" if successful_tests >= len(basic_questions) * 0.8 else "failed"
            self.test_results[test_name]["details"] = {
                "total_questions": len(basic_questions),
                "successful_tests": successful_tests,
                "success_rate": successful_tests / len(basic_questions),
                "avg_processing_time": avg_processing_time,
                "results": results
            }
            
            logger.info(f"✅ 기본 기능 테스트 완료: {successful_tests}/{len(basic_questions)} 성공")
            
        except Exception as e:
            self.test_results[test_name]["status"] = "failed"
            self.test_results[test_name]["error"] = str(e)
            logger.error(f"❌ 기본 기능 테스트 실패: {str(e)}")
    
    def test_advanced_functionality(self):
        """고급 기능 테스트"""
        logger.info("🚀 고급 기능 테스트 시작")
        
        test_name = "advanced_functionality"
        self.test_results[test_name] = {
            "status": "running",
            "start_time": time.time(),
            "details": {}
        }
        
        try:
            # 벡터스토어 초기화
            vectorstore = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            # 고급 기능 테스트
            advanced_tests = {}
            
            # 1. Corrective RAG 테스트
            try:
                corrective_rag = CorrectiveRAG(vectorstore)
                edge_questions = self.test_questions["edge_cases"]
                
                corrective_results = []
                for question in edge_questions:
                    start_time = time.time()
                    try:
                        docs, metadata = corrective_rag.perform_corrective_search(question, k=5)
                        processing_time = time.time() - start_time
                        
                        corrective_results.append({
                            "question": question,
                            "num_docs": len(docs),
                            "search_iterations": metadata.get("search_iterations", 0),
                            "query_rewritten": metadata.get("query_rewritten", False),
                            "processing_time": processing_time,
                            "success": True
                        })
                    except Exception as e:
                        corrective_results.append({
                            "question": question,
                            "error": str(e),
                            "success": False
                        })
                
                advanced_tests["corrective_rag"] = {
                    "status": "passed",
                    "results": corrective_results
                }
                
            except Exception as e:
                advanced_tests["corrective_rag"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # 2. Reranking 테스트
            try:
                reranker = DocumentReranker()
                
                # 샘플 문서 생성 (실제로는 벡터스토어에서 가져와야 함)
                from langchain.schema import Document
                sample_docs = [
                    Document(page_content="이 금융상품의 이자율은 연 15%입니다.", metadata={"source": "test1"}),
                    Document(page_content="수수료는 월 1,000원입니다.", metadata={"source": "test2"}),
                    Document(page_content="대출 한도는 1억원입니다.", metadata={"source": "test3"})
                ]
                
                rerank_results = []
                for method in ["llm", "tfidf", "hybrid", "mmr"]:
                    start_time = time.time()
                    try:
                        reranked_docs, scores, metadata = reranker.rerank_documents(
                            "이자율은 얼마인가요?", sample_docs, method=method, top_k=3
                        )
                        processing_time = time.time() - start_time
                        
                        rerank_results.append({
                            "method": method,
                            "num_docs": len(reranked_docs),
                            "avg_score": sum(scores) / len(scores) if scores else 0,
                            "processing_time": processing_time,
                            "success": True
                        })
                    except Exception as e:
                        rerank_results.append({
                            "method": method,
                            "error": str(e),
                            "success": False
                        })
                
                advanced_tests["reranking"] = {
                    "status": "passed",
                    "results": rerank_results
                }
                
            except Exception as e:
                advanced_tests["reranking"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # 3. NER 테스트
            try:
                ner = FinancialNER()
                
                ner_results = []
                for question in self.test_questions["ner"]:
                    try:
                        enhanced_query, entities = ner.enhance_query_with_entities(question)
                        financial_numbers = ner.extract_financial_numbers(question)
                        
                        ner_results.append({
                            "question": question,
                            "enhanced_query": enhanced_query,
                            "num_entities": len(entities),
                            "entity_types": [e.entity_type.value for e in entities],
                            "financial_numbers": financial_numbers,
                            "success": True
                        })
                    except Exception as e:
                        ner_results.append({
                            "question": question,
                            "error": str(e),
                            "success": False
                        })
                
                advanced_tests["ner"] = {
                    "status": "passed",
                    "results": ner_results
                }
                
            except Exception as e:
                advanced_tests["ner"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # 결과 분석
            passed_tests = sum(1 for test in advanced_tests.values() if test.get("status") == "passed")
            total_tests = len(advanced_tests)
            
            self.test_results[test_name]["status"] = "passed" if passed_tests >= total_tests * 0.8 else "failed"
            self.test_results[test_name]["details"] = {
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "success_rate": passed_tests / total_tests,
                "test_details": advanced_tests
            }
            
            logger.info(f"✅ 고급 기능 테스트 완료: {passed_tests}/{total_tests} 성공")
            
        except Exception as e:
            self.test_results[test_name]["status"] = "failed"
            self.test_results[test_name]["error"] = str(e)
            logger.error(f"❌ 고급 기능 테스트 실패: {str(e)}")
    
    def test_integrated_system(self):
        """통합 시스템 테스트"""
        logger.info("🔗 통합 시스템 테스트 시작")
        
        test_name = "integrated_system"
        self.test_results[test_name] = {
            "status": "running",
            "start_time": time.time(),
            "details": {}
        }
        
        try:
            # 벡터스토어 초기화
            vectorstore = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            # 고급 RAG 시스템 초기화
            advanced_rag = AdvancedRAGSystem(
                vectorstore=vectorstore,
                enable_corrective_rag=True,
                enable_reranking=True,
                enable_ner=True
            )
            
            # 통합 테스트 질문
            integrated_questions = self.test_questions["advanced"]
            results = []
            
            for question in integrated_questions:
                start_time = time.time()
                try:
                    response = advanced_rag.process_query(question)
                    processing_time = time.time() - start_time
                    
                    results.append({
                        "question": question,
                        "answer_length": len(response.get("answer", "")),
                        "num_sources": response.get("num_sources", 0),
                        "num_entities": len(response.get("entities", [])),
                        "relevance_scores": response.get("relevance_scores", []),
                        "components_used": response.get("pipeline_metadata", {}).get("components_used", []),
                        "processing_time": processing_time,
                        "success": True
                    })
                    
                except Exception as e:
                    results.append({
                        "question": question,
                        "error": str(e),
                        "success": False
                    })
            
            # 성능 메트릭 계산
            successful_tests = sum(1 for r in results if r.get("success", False))
            avg_processing_time = sum(r.get("processing_time", 0) for r in results if r.get("success")) / max(successful_tests, 1)
            avg_relevance_score = sum(
                sum(r.get("relevance_scores", [])) / len(r.get("relevance_scores", [])) 
                for r in results if r.get("success") and r.get("relevance_scores")
            ) / max(successful_tests, 1)
            
            self.test_results[test_name]["status"] = "passed" if successful_tests >= len(integrated_questions) * 0.8 else "failed"
            self.test_results[test_name]["details"] = {
                "total_questions": len(integrated_questions),
                "successful_tests": successful_tests,
                "success_rate": successful_tests / len(integrated_questions),
                "avg_processing_time": avg_processing_time,
                "avg_relevance_score": avg_relevance_score,
                "results": results
            }
            
            logger.info(f"✅ 통합 시스템 테스트 완료: {successful_tests}/{len(integrated_questions)} 성공")
            
        except Exception as e:
            self.test_results[test_name]["status"] = "failed"
            self.test_results[test_name]["error"] = str(e)
            logger.error(f"❌ 통합 시스템 테스트 실패: {str(e)}")
    
    def test_performance(self):
        """성능 테스트"""
        logger.info("⚡ 성능 테스트 시작")
        
        test_name = "performance"
        self.test_results[test_name] = {
            "status": "running",
            "start_time": time.time(),
            "details": {}
        }
        
        try:
            # 벡터스토어 초기화
            vectorstore = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            # 성능 테스트 질문
            performance_questions = self.test_questions["basic"][:3]  # 처음 3개만
            
            # 기본 RAG 성능
            basic_times = []
            for question in performance_questions:
                retriever = FinancialDocumentRetriever(vectorstore)
                start_time = time.time()
                try:
                    response = retriever.answer_question(question)
                    processing_time = time.time() - start_time
                    basic_times.append(processing_time)
                except:
                    basic_times.append(0)
            
            # 고급 RAG 성능
            advanced_times = []
            advanced_rag = AdvancedRAGSystem(vectorstore=vectorstore)
            for question in performance_questions:
                start_time = time.time()
                try:
                    response = advanced_rag.process_query(question)
                    processing_time = time.time() - start_time
                    advanced_times.append(processing_time)
                except:
                    advanced_times.append(0)
            
            # 성능 분석
            basic_avg_time = sum(basic_times) / len(basic_times)
            advanced_avg_time = sum(advanced_times) / len(advanced_times)
            performance_ratio = advanced_avg_time / basic_avg_time if basic_avg_time > 0 else 1
            
            self.test_results[test_name]["status"] = "passed" if performance_ratio < 3 else "failed"
            self.test_results[test_name]["details"] = {
                "basic_avg_time": basic_avg_time,
                "advanced_avg_time": advanced_avg_time,
                "performance_ratio": performance_ratio,
                "basic_times": basic_times,
                "advanced_times": advanced_times
            }
            
            logger.info(f"✅ 성능 테스트 완료: 기본 {basic_avg_time:.2f}s, 고급 {advanced_avg_time:.2f}s")
            
        except Exception as e:
            self.test_results[test_name]["status"] = "failed"
            self.test_results[test_name]["error"] = str(e)
            logger.error(f"❌ 성능 테스트 실패: {str(e)}")
    
    def generate_report(self):
        """테스트 결과 리포트 생성"""
        logger.info("📊 테스트 결과 리포트 생성")
        
        total_time = time.time() - self.start_time
        
        # 전체 결과 분석
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "passed")
        failed_tests = total_tests - passed_tests
        
        # 리포트 생성
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "total_time": total_time
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
            "recommendations": self._generate_recommendations()
        }
        
        # 리포트 저장
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 콘솔 출력
        print("\n" + "="*60)
        print("🧪 테스트 결과 요약")
        print("="*60)
        print(f"총 테스트: {total_tests}")
        print(f"성공: {passed_tests}")
        print(f"실패: {failed_tests}")
        print(f"성공률: {passed_tests/total_tests*100:.1f}%")
        print(f"총 소요시간: {total_time:.2f}초")
        print(f"리포트 파일: {report_file}")
        print("="*60)
        
        # 개별 테스트 결과
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result.get("status") == "passed" else "❌"
            print(f"{status_icon} {test_name}: {result.get('status', 'unknown')}")
        
        logger.info(f"📊 테스트 리포트 생성 완료: {report_file}")
    
    def _generate_recommendations(self) -> List[str]:
        """테스트 결과 기반 권장사항 생성"""
        recommendations = []
        
        for test_name, result in self.test_results.items():
            if result.get("status") == "failed":
                if test_name == "environment_setup":
                    recommendations.append("환경 설정을 확인하고 API 키를 올바르게 설정하세요.")
                elif test_name == "basic_functionality":
                    recommendations.append("기본 기능을 점검하고 벡터 데이터베이스 상태를 확인하세요.")
                elif test_name == "advanced_functionality":
                    recommendations.append("고급 기능의 의존성을 확인하고 필요한 패키지를 설치하세요.")
                elif test_name == "integrated_system":
                    recommendations.append("통합 시스템의 설정을 확인하고 컴포넌트 간 연결을 점검하세요.")
                elif test_name == "performance":
                    recommendations.append("성능 최적화를 고려하고 시스템 리소스를 점검하세요.")
        
        if not recommendations:
            recommendations.append("모든 테스트가 통과했습니다! 시스템이 정상적으로 작동하고 있습니다.")
        
        return recommendations

def main():
    """메인 실행 함수"""
    print("🧪 금융상품 약관 AI 도우미 테스트 시작")
    print("="*60)
    
    # 테스트 실행기 초기화
    test_runner = TestRunner()
    
    # 모든 테스트 실행
    results = test_runner.run_all_tests()
    
    print("\n🎯 테스트 완료!")
    return results

if __name__ == "__main__":
    main()
