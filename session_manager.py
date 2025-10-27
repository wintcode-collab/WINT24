import threading
import time
import requests
import base64
import os
from datetime import datetime, timedelta

class SessionManager:
    """?”ë ˆê·¸ë¨ ?¸ì…˜ ?êµ¬ ê´€ë¦??´ë˜??- ?¨ìˆœ?”ëœ ë²„ì „"""
    
    def __init__(self):
        self.running = False
        self.refresh_thread = None
        self.firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
        
    def start_session_refresh(self):
        """?¸ì…˜ ê°±ì‹  ?œì‘"""
        if self.running:
            return
            
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_sessions_loop, daemon=True)
        self.refresh_thread.start()
        print("?”„ ?¸ì…˜ ê°±ì‹  ?œë¹„???œì‘??)
        
    def stop_session_refresh(self):
        """?¸ì…˜ ê°±ì‹  ì¤‘ì?"""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join()
        print("?¹ï¸ ?¸ì…˜ ê°±ì‹  ?œë¹„??ì¤‘ì???)
        
    def _refresh_sessions_loop(self):
        """?¸ì…˜ ê°±ì‹  ë£¨í”„"""
        while self.running:
            try:
                self._refresh_all_sessions()
                # 30ë¶„ë§ˆ???¸ì…˜ ê°±ì‹ 
                time.sleep(30 * 60)  # 30ë¶?            except Exception as e:
                print(f"???¸ì…˜ ê°±ì‹  ?¤ë¥˜: {e}")
                time.sleep(5 * 60)  # ?¤ë¥˜ ??5ë¶????¬ì‹œ??                
    def _refresh_all_sessions(self):
        """ëª¨ë“  ?¸ì…˜ ê°±ì‹  - ?¨ìˆœ?”ëœ ë²„ì „"""
        try:
            # Firebase?ì„œ ëª¨ë“  ?”ë ˆê·¸ë¨ ê³„ì • ê°€?¸ì˜¤ê¸?            accounts_url = f"{self.firebase_url}/users/wint365/telegram_accounts.json"
            response = requests.get(accounts_url)
            
            if response.status_code == 200:
                accounts_data = response.json()
                if accounts_data and isinstance(accounts_data, dict):
                    for account_id, account_info in accounts_data.items():
                        # account_infoê°€ ?•ì…”?ˆë¦¬?¸ì? ?•ì¸?˜ê³ , ?¤ì œ ê³„ì • ?°ì´?°ì¸ì§€ ?•ì¸
                        if isinstance(account_info, dict) and 'phone' in account_info:
                            account_info['account_id'] = account_id  # account_id ì¶”ê?
                            self._refresh_single_session(account_info)
                        elif isinstance(account_info, dict):
                            # ?•ì…”?ˆë¦¬?´ì?ë§?ê³„ì • ?°ì´?°ê? ?„ë‹Œ ê²½ìš° (lastRefresh, status ??
                            print(f"?¹ï¸ ë©”í??°ì´??ê±´ë„ˆ?€: {account_id}")
                        else:
                            # ë¬¸ì?´ì¸ ê²½ìš° (lastRefresh, status ??
                            print(f"?¹ï¸ ë©”í??°ì´??ê±´ë„ˆ?€: {account_id}")
                        
        except Exception as e:
            print(f"???¸ì…˜ ëª©ë¡ ì¡°íšŒ ?¤ë¥˜: {e}")
            
    def _refresh_single_session(self, account_info):
        """?¨ì¼ ?¸ì…˜ ê°±ì‹  - ?¨ìˆœ?”ëœ ë²„ì „"""
        try:
            # account_infoê°€ ?•ì…”?ˆë¦¬?¸ì? ?•ì¸
            if not isinstance(account_info, dict):
                print(f"???˜ëª»??ê³„ì • ?•ë³´ ?•ì‹: {account_info}")
                return
                
            phone = account_info.get('phone', '')
            account_id = account_info.get('account_id', '')
            
            if not phone:
                print(f"???„í™”ë²ˆí˜¸ ?†ìŒ: {account_info}")
                return
                
            print(f"?”„ ?¸ì…˜ ?íƒœ ê°±ì‹ : {phone}")
            
            # ?¸ì…˜ ?°ì´?°ê? ?ˆëŠ”ì§€ ?•ì¸
            session_data = account_info.get('sessionData')
            if not session_data:
                print(f"???¸ì…˜ ?°ì´???†ìŒ: {phone}")
                return
            
            # Firebase??ê°±ì‹  ?œê°„ë§??…ë°?´íŠ¸ (?¤ì œ ?¸ì…˜ ê°±ì‹ ?€ ?¬ìš© ?œì—ë§?
            update_data = {
                'lastRefresh': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'active'
            }
            
            if not account_id:
                print(f"??ê³„ì • ID ?†ìŒ: {phone}")
                return
                
            update_url = f"{self.firebase_url}/users/wint365/telegram_accounts/{account_id}.json"
            response = requests.patch(update_url, json=update_data)
            
            if response.status_code == 200:
                print(f"???¸ì…˜ ?íƒœ ê°±ì‹  ?„ë£Œ: {phone}")
            else:
                print(f"???¸ì…˜ ?íƒœ ê°±ì‹  ?¤íŒ¨: {phone} - {response.status_code}")
            
        except Exception as e:
            phone = account_info.get('phone', 'Unknown') if isinstance(account_info, dict) else 'Unknown'
            print(f"???¸ì…˜ ê°±ì‹  ?¤íŒ¨ ({phone}): {e}")
            
    def manual_refresh_session(self, account_info):
        """?˜ë™ ?¸ì…˜ ê°±ì‹ """
        self._refresh_single_session(account_info)

# ?„ì—­ ?¸ì…˜ ë§¤ë‹ˆ?€ ?¸ìŠ¤?´ìŠ¤
session_manager = SessionManager()

def start_session_service():
    """?¸ì…˜ ?œë¹„???œì‘"""
    session_manager.start_session_refresh()

def stop_session_service():
    """?¸ì…˜ ?œë¹„??ì¤‘ì?"""
    session_manager.stop_session_refresh()

def refresh_session_now(account_info):
    """ì¦‰ì‹œ ?¸ì…˜ ê°±ì‹ """
    session_manager.manual_refresh_session(account_info)
