import threading
import time
import requests
import base64
import os
from datetime import datetime, timedelta

class SessionManager:
    """?�레그램 ?�션 ?�구 관�??�래??- ?�순?�된 버전"""
    
    def __init__(self):
        self.running = False
        self.refresh_thread = None
        self.firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
        
    def start_session_refresh(self):
        """?�션 갱신 ?�작"""
        if self.running:
            return
            
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_sessions_loop, daemon=True)
        self.refresh_thread.start()
        print("?�� ?�션 갱신 ?�비???�작??)
        
    def stop_session_refresh(self):
        """?�션 갱신 중�?"""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join()
        print("?�️ ?�션 갱신 ?�비??중�???)
        
    def _refresh_sessions_loop(self):
        """?�션 갱신 루프"""
        while self.running:
            try:
                self._refresh_all_sessions()
                # 30분마???�션 갱신
                time.sleep(30 * 60)  # 30�?            except Exception as e:
                print(f"???�션 갱신 ?�류: {e}")
                time.sleep(5 * 60)  # ?�류 ??5�????�시??                
    def _refresh_all_sessions(self):
        """모든 ?�션 갱신 - ?�순?�된 버전"""
        try:
            # Firebase?�서 모든 ?�레그램 계정 가?�오�?            accounts_url = f"{self.firebase_url}/users/wint365/telegram_accounts.json"
            response = requests.get(accounts_url)
            
            if response.status_code == 200:
                accounts_data = response.json()
                if accounts_data and isinstance(accounts_data, dict):
                    for account_id, account_info in accounts_data.items():
                        # account_info가 ?�셔?�리?��? ?�인?�고, ?�제 계정 ?�이?�인지 ?�인
                        if isinstance(account_info, dict) and 'phone' in account_info:
                            account_info['account_id'] = account_id  # account_id 추�?
                            self._refresh_single_session(account_info)
                        elif isinstance(account_info, dict):
                            # ?�셔?�리?��?�?계정 ?�이?��? ?�닌 경우 (lastRefresh, status ??
                            print(f"?�️ 메�??�이??건너?�: {account_id}")
                        else:
                            # 문자?�인 경우 (lastRefresh, status ??
                            print(f"?�️ 메�??�이??건너?�: {account_id}")
                        
        except Exception as e:
            print(f"???�션 목록 조회 ?�류: {e}")
            
    def _refresh_single_session(self, account_info):
        """?�일 ?�션 갱신 - ?�순?�된 버전"""
        try:
            # account_info가 ?�셔?�리?��? ?�인
            if not isinstance(account_info, dict):
                print(f"???�못??계정 ?�보 ?�식: {account_info}")
                return
                
            phone = account_info.get('phone', '')
            account_id = account_info.get('account_id', '')
            
            if not phone:
                print(f"???�화번호 ?�음: {account_info}")
                return
                
            print(f"?�� ?�션 ?�태 갱신: {phone}")
            
            # ?�션 ?�이?��? ?�는지 ?�인
            session_data = account_info.get('sessionData')
            if not session_data:
                print(f"???�션 ?�이???�음: {phone}")
                return
            
            # Firebase??갱신 ?�간�??�데?�트 (?�제 ?�션 갱신?� ?�용 ?�에�?
            update_data = {
                'lastRefresh': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'active'
            }
            
            if not account_id:
                print(f"??계정 ID ?�음: {phone}")
                return
                
            update_url = f"{self.firebase_url}/users/wint365/telegram_accounts/{account_id}.json"
            response = requests.patch(update_url, json=update_data)
            
            if response.status_code == 200:
                print(f"???�션 ?�태 갱신 ?�료: {phone}")
            else:
                print(f"???�션 ?�태 갱신 ?�패: {phone} - {response.status_code}")
            
        except Exception as e:
            phone = account_info.get('phone', 'Unknown') if isinstance(account_info, dict) else 'Unknown'
            print(f"???�션 갱신 ?�패 ({phone}): {e}")
            
    def manual_refresh_session(self, account_info):
        """?�동 ?�션 갱신"""
        self._refresh_single_session(account_info)

# ?�역 ?�션 매니?� ?�스?�스
session_manager = SessionManager()

def start_session_service():
    """?�션 ?�비???�작"""
    session_manager.start_session_refresh()

def stop_session_service():
    """?�션 ?�비??중�?"""
    session_manager.stop_session_refresh()

def refresh_session_now(account_info):
    """즉시 ?�션 갱신"""
    session_manager.manual_refresh_session(account_info)
