import threading
import time
import requests
import base64
import os
from datetime import datetime, timedelta

class SessionManager:
    """텔레그램 세션 영구 관리 클래스 - 단순화된 버전"""
    
    def __init__(self):
        self.running = False
        self.refresh_thread = None
        self.firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
        
    def start_session_refresh(self):
        """세션 갱신 시작"""
        if self.running:
            return
            
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_sessions_loop, daemon=True)
        self.refresh_thread.start()
        print("🔄 세션 갱신 서비스 시작됨")
        
    def stop_session_refresh(self):
        """세션 갱신 중지"""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join()
        print("⏹️ 세션 갱신 서비스 중지됨")
        
    def _refresh_sessions_loop(self):
        """세션 갱신 루프"""
        while self.running:
            try:
                self._refresh_all_sessions()
                # 30분마다 세션 갱신
                time.sleep(30 * 60)  # 30분
            except Exception as e:
                print(f"❌ 세션 갱신 오류: {e}")
                time.sleep(5 * 60)  # 오류 시 5분 후 재시도
                
    def _refresh_all_sessions(self):
        """모든 세션 갱신 - 단순화된 버전"""
        try:
            # Firebase에서 모든 텔레그램 계정 가져오기
            accounts_url = f"{self.firebase_url}/users/wint365/telegram_accounts.json"
            response = requests.get(accounts_url)
            
            if response.status_code == 200:
                accounts_data = response.json()
                if accounts_data and isinstance(accounts_data, dict):
                    for account_id, account_info in accounts_data.items():
                        # account_info가 딕셔너리인지 확인하고, 실제 계정 데이터인지 확인
                        if isinstance(account_info, dict) and 'phone' in account_info:
                            account_info['account_id'] = account_id  # account_id 추가
                            self._refresh_single_session(account_info)
                        elif isinstance(account_info, dict):
                            # 딕셔너리이지만 계정 데이터가 아닌 경우 (lastRefresh, status 등)
                            print(f"ℹ️ 메타데이터 건너뜀: {account_id}")
                        else:
                            # 문자열인 경우 (lastRefresh, status 등)
                            print(f"ℹ️ 메타데이터 건너뜀: {account_id}")
                        
        except Exception as e:
            print(f"❌ 세션 목록 조회 오류: {e}")
            
    def _refresh_single_session(self, account_info):
        """단일 세션 갱신 - 단순화된 버전"""
        try:
            # account_info가 딕셔너리인지 확인
            if not isinstance(account_info, dict):
                print(f"❌ 잘못된 계정 정보 형식: {account_info}")
                return
                
            phone = account_info.get('phone', '')
            account_id = account_info.get('account_id', '')
            
            if not phone:
                print(f"❌ 전화번호 없음: {account_info}")
                return
                
            print(f"🔄 세션 상태 갱신: {phone}")
            
            # 세션 데이터가 있는지 확인
            session_data = account_info.get('sessionData')
            if not session_data:
                print(f"❌ 세션 데이터 없음: {phone}")
                return
            
            # Firebase에 갱신 시간만 업데이트 (실제 세션 갱신은 사용 시에만)
            update_data = {
                'lastRefresh': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'active'
            }
            
            if not account_id:
                print(f"❌ 계정 ID 없음: {phone}")
                return
                
            update_url = f"{self.firebase_url}/users/wint365/telegram_accounts/{account_id}.json"
            response = requests.patch(update_url, json=update_data)
            
            if response.status_code == 200:
                print(f"✅ 세션 상태 갱신 완료: {phone}")
            else:
                print(f"❌ 세션 상태 갱신 실패: {phone} - {response.status_code}")
            
        except Exception as e:
            phone = account_info.get('phone', 'Unknown') if isinstance(account_info, dict) else 'Unknown'
            print(f"❌ 세션 갱신 실패 ({phone}): {e}")
            
    def manual_refresh_session(self, account_info):
        """수동 세션 갱신"""
        self._refresh_single_session(account_info)

# 전역 세션 매니저 인스턴스
session_manager = SessionManager()

def start_session_service():
    """세션 서비스 시작"""
    session_manager.start_session_refresh()

def stop_session_service():
    """세션 서비스 중지"""
    session_manager.stop_session_refresh()

def refresh_session_now(account_info):
    """즉시 세션 갱신"""
    session_manager.manual_refresh_session(account_info)