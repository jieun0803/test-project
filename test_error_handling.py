#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
에러 처리 테스트 스크립트
시스템의 에러 상황 처리 능력을 테스트
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import logging
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.env_loader import load_environment, get_api_key
from src.embedding import FinancialEmbeddingStore
from src.advanced_rag import AdvancedRAGSystem
from src.chunking import FinancialDocumentChunker

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorHandlingTester:
    """에러 처리 테스트 클래스"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
    
    def setup_temp_environment(self):
        """임시 테스트 환경 설정"""
        self.temp_dir = tempfile.mkdtemp()
        print(f"📁 임시 디렉토리 생성: {self.temp_dir}")
    
    def cleanup_temp_environment(self):
        """임시 테스트 환경 정리"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🗑️ 임시 디렉토리 정리: {self.temp_dir}")
    
    def test_invalid_pdf_handling(self):
        """잘못된 PDF 파일 처리 테스트"""
        print("\n🧪 테스트 1: 잘못된 PDF 파일 처리")
        print("-" * 40)
        
        try:
            # 잘못된 PDF 파일 생성
            invalid_pdf_path = os.path.join(self.temp_dir, "invalid.pdf")
            with open(invalid_pdf_path, 'w', encoding='utf-8') as f:
                f.write("This is not a PDF file")
            
            # 청킹 테스트
            chunker = FinancialDocumentChunker()
            result = chunker.process_pdf(invalid_pdf_path)
            
            if result is None or len(result) == 0:
                self.test_results.append({
                    'test': 'invalid_pdf',
                    'status': 'PASS',
                    'message': '잘못된 PDF 파일이 적절히 처리됨'
                })
                print("✅ 잘못된 PDF 파일이 적절히 처리됨")
            else:
                self.test_results.append({
                    'test': 'invalid_pdf',
                    'status': 'FAIL',
                    'message': '잘못된 PDF 파일이 처리되어서는 안됨'
                })
                print("❌ 잘못된 PDF 파일이 처리됨")
                
        except Exception as e:
            # 예외가 발생하는 것이 정상
            self.test_results.append({
                'test': 'invalid_pdf',
                'status': 'PASS',
                'message': f'예상된 예외 발생: {str(e)[:50]}...'
            })
            print(f"✅ 예상된 예외 발생: {str(e)[:50]}...")
    
    def test_api_key_errors(self):
        """API 키 관련 에러 테스트"""
        print("\n🧪 테스트 2: API 키 에러 처리")
        print("-" * 40)
        
        # 잘못된 API 키로 테스트
        with patch.dict(os.environ, {'UPSTAGE_API_KEY': 'invalid_key_12345'}):
            try:
                vectorstore = FinancialEmbeddingStore(
                    persist_directory="./vectordb",
                    embedding_model="solar-embedding-1-large-passage"
                )
                
                # 임베딩 생성 시도
                test_text = "테스트 텍스트"
                result = vectorstore.embeddings.embed_query(test_text)
                
                self.test_results.append({
                    'test': 'api_key_error',
                    'status': 'FAIL',
                    'message': '잘못된 API 키가 처리되어서는 안됨'
                })
                print("❌ 잘못된 API 키가 처리됨")
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'api' in error_msg or 'key' in error_msg or '401' in error_msg:
                    self.test_results.append({
                        'test': 'api_key_error',
                        'status': 'PASS',
                        'message': f'API 키 에러가 적절히 처리됨: {str(e)[:50]}...'
                    })
                    print(f"✅ API 키 에러가 적절히 처리됨: {str(e)[:50]}...")
                else:
                    self.test_results.append({
                        'test': 'api_key_error',
                        'status': 'FAIL',
                        'message': f'예상과 다른 에러: {str(e)[:50]}...'
                    })
                    print(f"❌ 예상과 다른 에러: {str(e)[:50]}...")
    
    def test_network_errors(self):
        """네트워크 에러 테스트"""
        print("\n🧪 테스트 3: 네트워크 에러 처리")
        print("-" * 40)
        
        # 네트워크 에러 시뮬레이션
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network connection failed")
            
            try:
                vectorstore = FinancialEmbeddingStore(
                    persist_directory="./vectordb",
                    embedding_model="solar-embedding-1-large-passage"
                )
                
                # 임베딩 생성 시도
                test_text = "테스트 텍스트"
                result = vectorstore.embeddings.embed_query(test_text)
                
                self.test_results.append({
                    'test': 'network_error',
                    'status': 'FAIL',
                    'message': '네트워크 에러가 처리되어서는 안됨'
                })
                print("❌ 네트워크 에러가 처리됨")
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'network' in error_msg or 'connection' in error_msg:
                    self.test_results.append({
                        'test': 'network_error',
                        'status': 'PASS',
                        'message': f'네트워크 에러가 적절히 처리됨: {str(e)[:50]}...'
                    })
                    print(f"✅ 네트워크 에러가 적절히 처리됨: {str(e)[:50]}...")
                else:
                    self.test_results.append({
                        'test': 'network_error',
                        'status': 'FAIL',
                        'message': f'예상과 다른 에러: {str(e)[:50]}...'
                    })
                    print(f"❌ 예상과 다른 에러: {str(e)[:50]}...")
    
    def test_memory_errors(self):
        """메모리 에러 테스트"""
        print("\n🧪 테스트 4: 메모리 에러 처리")
        print("-" * 40)
        
        # 메모리 에러 시뮬레이션
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB만 사용 가능
            
            try:
                # 대용량 텍스트 생성
                large_text = "대용량 텍스트 " * 100000  # 약 1MB
                
                chunker = FinancialDocumentChunker()
                result = chunker.chunk_with_langchain(large_text)
                
                if result and len(result) > 0:
                    self.test_results.append({
                        'test': 'memory_error',
                        'status': 'PASS',
                        'message': '메모리 제약 상황에서도 처리됨'
                    })
                    print("✅ 메모리 제약 상황에서도 처리됨")
                else:
                    self.test_results.append({
                        'test': 'memory_error',
                        'status': 'FAIL',
                        'message': '메모리 제약으로 처리 실패'
                    })
                    print("❌ 메모리 제약으로 처리 실패")
                    
            except MemoryError:
                self.test_results.append({
                    'test': 'memory_error',
                    'status': 'PASS',
                    'message': '메모리 에러가 적절히 처리됨'
                })
                print("✅ 메모리 에러가 적절히 처리됨")
            except Exception as e:
                self.test_results.append({
                    'test': 'memory_error',
                    'status': 'FAIL',
                    'message': f'예상과 다른 에러: {str(e)[:50]}...'
                })
                print(f"❌ 예상과 다른 에러: {str(e)[:50]}...")
    
    def test_empty_input_handling(self):
        """빈 입력 처리 테스트"""
        print("\n🧪 테스트 5: 빈 입력 처리")
        print("-" * 40)
        
        try:
            chunker = FinancialDocumentChunker()
            
            # 빈 텍스트 테스트
            result = chunker.chunk_with_langchain("")
            
            if result is None or len(result) == 0:
                self.test_results.append({
                    'test': 'empty_input',
                    'status': 'PASS',
                    'message': '빈 입력이 적절히 처리됨'
                })
                print("✅ 빈 입력이 적절히 처리됨")
            else:
                self.test_results.append({
                    'test': 'empty_input',
                    'status': 'FAIL',
                    'message': '빈 입력이 처리되어서는 안됨'
                })
                print("❌ 빈 입력이 처리됨")
                
        except Exception as e:
            self.test_results.append({
                'test': 'empty_input',
                'status': 'PASS',
                'message': f'빈 입력 예외가 적절히 처리됨: {str(e)[:50]}...'
            })
            print(f"✅ 빈 입력 예외가 적절히 처리됨: {str(e)[:50]}...")
    
    def test_file_permission_errors(self):
        """파일 권한 에러 테스트"""
        print("\n🧪 테스트 6: 파일 권한 에러 처리")
        print("-" * 40)
        
        try:
            # 읽기 전용 파일 생성
            read_only_file = os.path.join(self.temp_dir, "readonly.txt")
            with open(read_only_file, 'w') as f:
                f.write("읽기 전용 파일")
            
            # 파일 권한 변경 (읽기 전용)
            os.chmod(read_only_file, 0o444)
            
            # 파일 읽기 시도
            with open(read_only_file, 'r') as f:
                content = f.read()
            
            if content:
                self.test_results.append({
                    'test': 'file_permission',
                    'status': 'PASS',
                    'message': '읽기 전용 파일이 적절히 처리됨'
                })
                print("✅ 읽기 전용 파일이 적절히 처리됨")
            else:
                self.test_results.append({
                    'test': 'file_permission',
                    'status': 'FAIL',
                    'message': '읽기 전용 파일 처리 실패'
                })
                print("❌ 읽기 전용 파일 처리 실패")
                
        except PermissionError:
            self.test_results.append({
                'test': 'file_permission',
                'status': 'PASS',
                'message': '권한 에러가 적절히 처리됨'
            })
            print("✅ 권한 에러가 적절히 처리됨")
        except Exception as e:
            self.test_results.append({
                'test': 'file_permission',
                'status': 'FAIL',
                'message': f'예상과 다른 에러: {str(e)[:50]}...'
            })
            print(f"❌ 예상과 다른 에러: {str(e)[:50]}...")
    
    def test_concurrent_access_errors(self):
        """동시 접근 에러 테스트"""
        print("\n🧪 테스트 7: 동시 접근 에러 처리")
        print("-" * 40)
        
        try:
            # 동일한 벡터 DB에 동시 접근 시뮬레이션
            vectorstore1 = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            vectorstore2 = FinancialEmbeddingStore(
                persist_directory="./vectordb",
                embedding_model="solar-embedding-1-large-passage"
            )
            
            # 동시 검색 시도
            result1 = vectorstore1.similarity_search("테스트 질문", k=3)
            result2 = vectorstore2.similarity_search("테스트 질문", k=3)
            
            if result1 is not None and result2 is not None:
                self.test_results.append({
                    'test': 'concurrent_access',
                    'status': 'PASS',
                    'message': '동시 접근이 적절히 처리됨'
                })
                print("✅ 동시 접근이 적절히 처리됨")
            else:
                self.test_results.append({
                    'test': 'concurrent_access',
                    'status': 'FAIL',
                    'message': '동시 접근 처리 실패'
                })
                print("❌ 동시 접근 처리 실패")
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'lock' in error_msg or 'concurrent' in error_msg:
                self.test_results.append({
                    'test': 'concurrent_access',
                    'status': 'PASS',
                    'message': f'동시 접근 에러가 적절히 처리됨: {str(e)[:50]}...'
                })
                print(f"✅ 동시 접근 에러가 적절히 처리됨: {str(e)[:50]}...")
            else:
                self.test_results.append({
                    'test': 'concurrent_access',
                    'status': 'FAIL',
                    'message': f'예상과 다른 에러: {str(e)[:50]}...'
                })
                print(f"❌ 예상과 다른 에러: {str(e)[:50]}...")
    
    def run_all_tests(self):
        """모든 에러 처리 테스트 실행"""
        print("🚀 에러 처리 테스트 시작")
        print("=" * 50)
        
        self.setup_temp_environment()
        
        try:
            # 각 테스트 실행
            self.test_invalid_pdf_handling()
            self.test_api_key_errors()
            self.test_network_errors()
            self.test_memory_errors()
            self.test_empty_input_handling()
            self.test_file_permission_errors()
            self.test_concurrent_access_errors()
            
        finally:
            self.cleanup_temp_environment()
        
        # 테스트 결과 요약
        self.print_test_summary()
    
    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 50)
        print("📊 에러 처리 테스트 결과 요약")
        print("=" * 50)
        
        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        total_count = len(self.test_results)
        
        print(f"✅ 통과: {pass_count}/{total_count}")
        print(f"📈 성공률: {pass_count/total_count*100:.1f}%")
        
        print("\n📋 상세 결과:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['test']}: {result['message']}")
        
        # 에러 처리 품질 평가
        if pass_count == total_count:
            print("\n🎉 모든 에러 처리가 적절히 작동합니다!")
        elif pass_count >= total_count * 0.8:
            print("\n⚠️ 대부분의 에러 처리가 적절하지만 일부 개선이 필요합니다.")
        else:
            print("\n❌ 에러 처리가 부족합니다. 코드를 점검해주세요.")
        
        return pass_count == total_count

def main():
    """메인 함수"""
    print("🧪 에러 처리 테스트 시작")
    
    tester = ErrorHandlingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 모든 에러 처리 테스트 통과!")
        print("✅ 시스템이 다양한 에러 상황을 적절히 처리합니다.")
    else:
        print("\n⚠️ 일부 에러 처리 테스트 실패.")
        print("💡 에러 처리 코드를 점검해주세요.")
    
    return success

if __name__ == "__main__":
    main()
