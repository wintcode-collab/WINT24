#!/usr/bin/env python3
"""
백그라운드 자동전송 데몬
Render에서 실행되어 PC와 무관하게 계속 실행됨
"""
import requests
import asyncio
import base64
import tempfile
from telethon import TelegramClient
import time
import sys
from datetime import datetime

class AutoSenderDaemon:
    def __init__(self, user_email):
        self.user_email = user_email
        self.is_running = False
        self.temp_files = []
        
    def log(self, message):
        """로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def check_firebase_status(self):
        """Firebase에서 자동전송 상태 확인"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            status_url = f"{firebase_url}/users/{self.user_email}/auto_send_status.json"
            
            response = requests.get(status_url, timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                return status_data and status_data.get('is_running', False)
        except Exception as e:
            self.log(f"상태 확인 오류: {e}")
        return False
    
    def load_settings(self):
        """전송 설정 로드"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            settings_url = f"{firebase_url}/users/{self.user_email}/time_settings.json"
            
            response = requests.get(settings_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"설정 로드 오류: {e}")
        return None
    
    def load_pools(self):
        """풀 데이터 로드"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            pools_url = f"{firebase_url}/users/{self.user_email}/pools.json"
            
            response = requests.get(pools_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'pools' in data:
                    return data['pools']
        except Exception as e:
            self.log(f"풀 로드 오류: {e}")
        return None
    
    def load_groups(self):
        """그룹 데이터 로드"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            groups_url = f"{firebase_url}/users/{self.user_email}/group_selections.json"
            
            response = requests.get(groups_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"그룹 로드 오류: {e}")
        return None
    
    def load_messages(self):
        """메시지 데이터 로드"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            messages_url = f"{firebase_url}/users/{self.user_email}/forward_messages.json"
            
            response = requests.get(messages_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"메시지 로드 오류: {e}")
        return None
    
    def load_accounts(self):
        """계정 데이터 로드"""
        try:
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
            accounts_url = f"{firebase_url}/users/{self.user_email}/selected_accounts.json"
            
            response = requests.get(accounts_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"계정 로드 오류: {e}")
        return None
    
    def run(self):
        """데몬 메인 루프"""
        self.log("=" * 60)
        self.log("🚀 자동전송 데몬 시작")
        self.log(f"사용자: {self.user_email}")
        self.log("=" * 60)
        
        # 무한 루프 - Firebase 상태 확인
        while True:
            try:
                # Firebase에서 상태 확인
                should_run = self.check_firebase_status()
                
                if should_run and not self.is_running:
                    # 시작
                    self.log("📱 Firebase 상태: ON - 자동전송 시작")
                    self.is_running = True
                    # 별도 스레드에서 실행
                    import threading
                    thread = threading.Thread(target=self.run_auto_send, daemon=True)
                    thread.start()
                elif not should_run and self.is_running:
                    # 중지
                    self.log("🛑 Firebase 상태: OFF - 자동전송 중지")
                    self.is_running = False
                
                # 5초마다 상태 확인
                time.sleep(5)
                
            except KeyboardInterrupt:
                self.log("중지 신호 수신 - 종료")
                self.is_running = False
                break
            except Exception as e:
                self.log(f"데몬 오류: {e}")
                time.sleep(10)  # 오류 시 10초 대기
    
    def run_auto_send(self):
        """자동 전송 실행"""
        try:
            # 데이터 로드
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 초기 설정
            group_interval = 10
            pool_interval = 300
            pool_order = []
            
            if all([settings, pools, groups, messages, accounts]):
                group_interval = int(settings.get('group_interval_seconds', 10))
                pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                pool_order = self.create_pool_order(pools)
            
            # 무한 루프
            cycle_count = 0
            while self.is_running:
                # Firebase 상태 계속 확인
                if not self.check_firebase_status():
                    self.log("Firebase에서 OFF 신호 받음 - 중지")
                    self.is_running = False
                    break
                
                # 데이터 새로고침 (100 사이클마다)
                if cycle_count % 100 == 0:
                    self.log(f"데이터 새로고침 (사이클: {cycle_count})")
                    settings = self.load_settings()
                    pools = self.load_pools()
                    groups = self.load_groups()
                    messages = self.load_messages()
                    accounts = self.load_accounts()
                    
                    if all([settings, pools, groups, messages, accounts]):
                        group_interval = int(settings.get('group_interval_seconds', 10))
                        pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                        pool_order = self.create_pool_order(pools)
                
                if not pool_order:
                    self.log("풀 순서가 비어있습니다. 데이터 대기 중...")
                    time.sleep(10)
                    continue
                
                for pool_info in pool_order:
                    if not self.is_running:
                        break
                    
                    pool_name = pool_info['pool_name']
                    account_phone = pool_info['account_phone']
                    
                    self.log(f"📦 풀 {pool_name} 계정 {account_phone} 시작")
                    
                    account = self.find_account(accounts, account_phone)
                    if not account:
                        self.log(f"⚠️ 계정 {account_phone}을 찾을 수 없습니다.")
                        continue
                    
                    account_groups = self.get_account_groups(groups, account_phone)
                    if not account_groups:
                        self.log(f"⚠️ 계정 {account_phone}의 그룹이 없습니다.")
                        continue
                    
                    self.log(f"📋 총 {len(account_groups)}개 그룹에 메시지 전송")
                    
                    success = self.send_messages_to_groups(
                        account, account_groups, messages, group_interval
                    )
                    
                    if success:
                        self.log(f"✅ 풀 {pool_name} 계정 {account_phone} 완료")
                        
                        if pool_interval > 0:
                            minutes = pool_interval // 60
                            seconds = pool_interval % 60
                            if minutes > 0:
                                self.log(f"⏳ 풀 간 대기시간: {minutes}분 {seconds}초")
                            else:
                                self.log(f"⏳ 풀 간 대기시간: {seconds}초")
                            
                            waited = 0
                            while waited < pool_interval and self.is_running:
                                time.sleep(1)
                                waited += 1
                                if waited % 10 == 0:
                                    remaining = pool_interval - waited
                                    minutes = remaining // 60
                                    seconds = remaining % 60
                                    if minutes > 0:
                                        self.log(f"⏱️ 대기 중... 남은 시간: {minutes}분 {seconds}초")
                                    else:
                                        self.log(f"⏱️ 대기 중... 남은 시간: {seconds}초")
                    else:
                        self.log(f"❌ 풀 {pool_name} 계정 {account_phone} 전송 실패")
                
                cycle_count += 1
                        
        except Exception as e:
            self.log(f"자동 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    def create_pool_order(self, pools):
        """풀 로테이션 순서 생성"""
        pool_order = []
        max_pool_size = max(len(accounts) for accounts in pools.values()) if pools else 0
        
        for i in range(max_pool_size):
            for pool_name, accounts in pools.items():
                if i < len(accounts):
                    pool_order.append({
                        'pool_name': pool_name,
                        'account_phone': accounts[i]
                    })
        
        return pool_order
    
    def find_account(self, accounts, phone):
        """계정 찾기"""
        if isinstance(accounts, list):
            for account in accounts:
                if account.get('phone') == phone:
                    return account
        elif isinstance(accounts, dict):
            for account in accounts.values():
                if account.get('phone') == phone:
                    return account
        return None
    
    def get_account_groups(self, groups, account_phone):
        """계정의 그룹 목록 가져오기"""
        account_groups = []
        if isinstance(groups, dict):
            for group_id, group_data in groups.items():
                if group_data.get('account_phone') == account_phone:
                    selected_groups = group_data.get('selected_groups', [])
                    for group in selected_groups:
                        account_groups.append({
                            'id': group.get('id'),
                            'group_id': group.get('id'),
                            'title': group.get('title', 'Unknown')
                        })
        return account_groups
    
    def send_messages_to_groups(self, account, groups, messages, group_interval):
        """그룹들에 메시지 전송"""
        try:
            if not self.is_running:
                return False
            
            account_messages = self.get_account_messages(messages, account['phone'])
            if not account_messages:
                self.log(f"계정 {account.get('phone')}에 대한 메시지가 없습니다.")
                return False
            
            if not self.is_running:
                return False
            
            # 텔레그램 클라이언트 생성
            session_data = base64.b64decode(account['sessionData'])
            temp_session = tempfile.NamedTemporaryFile(delete=False, suffix='.session')
            temp_session.write(session_data)
            temp_session.close()
            self.temp_files.append(temp_session.name)
            
            api_id = account['apiId']
            api_hash = account['apiHash']
            
            # 비동기로 전송
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self.send_messages_async(
                        temp_session.name, api_id, api_hash, 
                        groups, account_messages, group_interval
                    )
                )
                return success
            finally:
                loop.close()
                
        except Exception as e:
            self.log(f"메시지 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            return True
    
    async def send_messages_async(self, session_path, api_id, api_hash, groups, messages, group_interval):
        """비동기로 메시지 전송"""
        client = TelegramClient(session_path, api_id, api_hash)
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                await client.connect()
                self.log(f"텔레그램 연결 성공 (시도 {retry + 1}/{max_retries})")
                break
            except Exception as connect_error:
                self.log(f"연결 실패 (시도 {retry + 1}/{max_retries}): {connect_error}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return False
        
        try:
            for group_info in groups:
                if not self.is_running:
                    break
                
                group_id = group_info.get('group_id')
                group_title = group_info.get('title', 'Unknown')
                
                if not group_id:
                    continue
                
                message_count = 0
                for message_data in messages:
                    if not self.is_running:
                        break
                    
                    source_chat_id = message_data.get('source_chat_id')
                    message_id = message_data.get('message_id')
                    channel_title = message_data.get('channel_title', 'Unknown')
                    
                    if not source_chat_id or not message_id:
                        continue
                    
                    try:
                        source_peer = await client.get_entity(source_chat_id)
                        target_peer = await client.get_entity(group_id)
                        
                        await client.forward_messages(
                            entity=target_peer,
                            messages=[message_id],
                            from_peer=source_peer
                        )
                        
                        message_count += 1
                        self.log(f"✅ 메시지 전달 성공: {channel_title} -> {group_title}")
                        
                    except Exception as e:
                        self.log(f"❌ 메시지 전달 실패 ({channel_title} -> {group_title}): {e}")
                
                if message_count > 0:
                    self.log(f"✅ 그룹 '{group_title}'에 {message_count}개 메시지 전송 성공")
                
                if group_interval > 0:
                    self.log(f"⏳ 다음 그룹 전송 대기시간: {group_interval}초")
                    waited = 0
                    while waited < group_interval and self.is_running:
                        await asyncio.sleep(1)
                        waited += 1
                else:
                    self.log(f"⏳ 다음 그룹으로 이동...")
            
            await client.disconnect()
            return True
            
        except Exception as e:
            try:
                await client.disconnect()
            except:
                pass
            self.log(f"전송 오류: {e}")
            return False
    
    def get_account_messages(self, messages, account_phone):
        """계정의 메시지 목록 가져오기"""
        account_messages = []
        
        if isinstance(messages, dict):
            for msg_id, msg_data in messages.items():
                if isinstance(msg_data, str):
                    continue
                
                if not isinstance(msg_data, dict):
                    continue
                
                if msg_data.get('account_phone') == account_phone:
                    selected_messages = msg_data.get('selected_messages', [])
                    
                    for msg in selected_messages:
                        if not isinstance(msg, dict):
                            continue
                        
                        source_chat_id = msg.get('group_id')
                        message_id = msg.get('id')
                        group_title = msg.get('group_title', 'Unknown')
                        
                        if source_chat_id and message_id:
                            account_messages.append({
                                'source_chat_id': source_chat_id,
                                'message_id': message_id,
                                'channel_title': group_title
                            })
        
        return account_messages
    
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        for temp_file in self.temp_files:
            try:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                self.log(f"파일 삭제 오류: {e}")
        self.temp_files = []


def main():
    """메인 함수"""
    # 사용자 이메일 확인
    if len(sys.argv) < 2:
        print("사용법: python auto_sender_daemon.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    
    daemon = AutoSenderDaemon(user_email)
    daemon.run()


if __name__ == "__main__":
    main()

