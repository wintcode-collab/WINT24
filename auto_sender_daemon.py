#!/usr/bin/env python3
"""
백그라운드 자동전송 데몬
Render에서 실행되어 PC와 무관하게 계속 실행됨
"""
import sys
import time
import requests
import asyncio
import base64
import tempfile
from telethon import TelegramClient
from datetime import datetime

# 즉시 출력
print("=" * 60)
print("🚀 auto_sender_daemon.py 시작")
print("=" * 60)
sys.stdout.flush()

class AutoSenderDaemon:
    def __init__(self, user_email):
        self.user_email = user_email
        self.is_running = False
        self.temp_files = []
        self.group_wait_times = {}  # {group_id: wait_until_timestamp}
        
    def log(self, message):
        """로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        sys.stdout.flush()
        
    def check_firebase_status(self):
        """DMA에서 자동전송 상태 확인"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
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
        
        # 무한 루프 - DMA 상태 확인
        while True:
            try:
                # DMA에서 상태 확인
                should_run = self.check_firebase_status()
                
                if should_run and not self.is_running:
                    # 시작
                    self.log("📱 DMA 상태: ON - 자동전송 시작")
                    self.is_running = True
                    # 별도 스레드에서 실행
                    import threading
                    thread = threading.Thread(target=self.run_auto_send, daemon=True)
                    thread.start()
                elif not should_run and self.is_running:
                    # 중지
                    self.log("🛑 DMA 상태: OFF - 자동전송 중지")
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
            # 데이터 로드 (한 번만 로드)
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 초기 설정
            group_interval = 10
            pool_interval = 300
            pool_accounts = {}
            
            if all([settings, pools, groups, messages, accounts]):
                self.log(f"✅ 데이터 로드 완료")
                self.log(f"  - 설정: {settings is not None}")
                self.log(f"  - 풀: {pools is not None}")
                self.log(f"  - 그룹: {groups is not None}")
                self.log(f"  - 메시지: {messages is not None}")
                self.log(f"  - 계정: {accounts is not None}")
                group_interval = int(settings.get('group_interval_seconds', 10))
                pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                pool_accounts = self.create_pool_order(pools)
                self.log(f"📊 풀 순서: {list(pool_accounts.keys())}")
            else:
                self.log(f"⚠️ 데이터 누락 - 설정:{settings is not None}, 풀:{pools is not None}, 그룹:{groups is not None}, 메시지:{messages is not None}, 계정:{accounts is not None}")
            
            # 각 풀을 독립적으로 무한 루프로 실행
            import threading
            pool_threads = []
            
            if not pool_accounts:
                self.log("⚠️ 풀 데이터가 없습니다.")
                return
                
            for idx, (pool_name, pool_accounts_list) in enumerate(pool_accounts.items()):
                if not pool_accounts_list:
                    self.log(f"⚠️ {pool_name}에 계정이 없습니다.")
                    continue
                    
                # 각 풀을 별도 스레드로 실행
                thread = threading.Thread(
                    target=self.run_pool_cycle,
                    args=(pool_name, pool_accounts_list, idx * pool_interval, accounts, groups, messages, group_interval),
                    daemon=True
                )
                thread.start()
                pool_threads.append(thread)
            
            # 모든 풀이 중지될 때까지 대기
            while self.is_running:
                # DMA 상태 확인 (5분마다)
                time.sleep(300)  # 5분
                if not self.check_firebase_status():
                    self.log("DMA에서 OFF 신호 받음 - 중지")
                    self.is_running = False
                    break
                        
        except Exception as e:
            self.log(f"자동 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
    
    def run_pool_cycle(self, pool_name, pool_accounts, start_delay, accounts, groups, messages, group_interval):
        """각 풀을 독립적으로 무한 루프로 실행"""
        # 시작 대기 (풀2는 5분 대기)
        if start_delay > 0:
            self.log(f"⏳ {pool_name} 시작 대기 중... ({start_delay//60}분)")
            waited = 0
            while waited < start_delay and self.is_running:
                time.sleep(1)
                waited += 1
                if waited % 10 == 0:
                    remaining = start_delay - waited
                    self.log(f"⏱️ {pool_name} 대기 중... {remaining//60}분 {remaining%60}초 남음")
        
        # 계정들을 그룹으로 나누어 처리
        if not pool_accounts:
            self.log(f"⚠️ {pool_name}에 계정 목록이 없습니다.")
            return
            
        account_count = len(pool_accounts)
        if account_count == 0:
            self.log(f"⚠️ {pool_name}에 계정이 없습니다.")
            return
        
        # 무한 루프로 풀 실행
        while self.is_running:
            try:
                # Group 0: 계정1만 처리
                self.log(f"📦 {pool_name} 계정1 전송 시작")
                idx = 0
                
                # 범위 체크
                if idx >= len(pool_accounts):
                    self.log(f"⚠️ {pool_name}에 계정이 없습니다.")
                    break
                
                account_data = pool_accounts[idx]
                if not account_data:
                    self.log(f"⚠️ {pool_name} 계정{idx+1} 데이터가 없습니다.")
                    break
                
                if isinstance(account_data, dict):
                    account_phone = account_data.get('account', account_data)
                else:
                    account_phone = account_data
                
                self.log(f"🔍 계정 찾기: {account_phone}")
                account = self.find_account(accounts, account_phone)
                if account:
                    self.log(f"✅ 계정 찾음: {account.get('phone')}")
                else:
                    self.log(f"❌ 계정을 찾을 수 없음: {account_phone}")
                if account:
                    account_groups_list = self.get_account_groups(groups, account_phone)
                    if account_groups_list:
                        self.send_account_messages(pool_name, account, account_groups_list, messages, group_interval, 1)
                
                if not self.is_running:
                    break
                
                # 이후 계정2,3과 계정4,1을 번갈아 반복
                group_sequence = 1  # 홀수: 계정2,3 / 짝수: 계정4,1
                
                while self.is_running:
                    if group_sequence % 2 == 1:  # 계정2,3 (홀수)
                        self.log(f"📦 {pool_name} 계정2,3 전송 시작")
                        current_groups = [1, 2] if account_count >= 3 else [1]
                    else:  # 계정4,1 (짝수)
                        self.log(f"📦 {pool_name} 계정4,1 전송 시작")
                        current_groups = [3, 0] if account_count >= 4 else []
                    
                    if not current_groups:
                        break
                    
                    # 그룹 내 계정들을 동시 처리
                    import threading
                    threads = []
                    
                    for idx in current_groups:
                        if idx >= len(pool_accounts):
                            continue
                        
                        account_data = pool_accounts[idx]
                        if not account_data:
                            continue
                        
                        if isinstance(account_data, dict):
                            account_phone = account_data.get('account', account_data)
                        else:
                            account_phone = account_data
                        
                        account = self.find_account(accounts, account_phone)
                        if not account:
                            continue
                        
                        account_groups_list = self.get_account_groups(groups, account_phone)
                        if not account_groups_list:
                            continue
                        
                        thread = threading.Thread(
                            target=self.send_account_messages,
                            args=(pool_name, account, account_groups_list, messages, group_interval, idx + 1),
                            daemon=True
                        )
                        thread.start()
                        threads.append(thread)
                    
                    # 모든 계정이 완료될 때까지 대기
                    for thread in threads:
                        thread.join()
                    
                    group_sequence += 1
                
            except Exception as e:
                self.log(f"❌ {pool_name} 사이클 오류: {e}")
                import traceback
                traceback.print_exc()
                # 오류 발생해도 계속 진행
                time.sleep(5)  # 5초 대기 후 재시도
    
    def send_account_messages(self, pool_name, account, account_groups, messages, group_interval, account_order):
        """계정별 메시지 전송"""
        try:
            if not account:
                self.log(f"⚠️ {pool_name} 계정{account_order} 정보가 없습니다.")
                return False
                
            if not account_groups:
                self.log(f"⚠️ {pool_name} 계정{account_order}의 그룹이 없습니다.")
                return False
                
            self.log(f"📋 {pool_name} 계정{account_order}: {len(account_groups)}개 그룹에 메시지 전송")
            success = self.send_messages_to_groups(account, account_groups, messages, group_interval)
            if success:
                self.log(f"✅ {pool_name} 계정{account_order} 완료")
            else:
                self.log(f"❌ {pool_name} 계정{account_order} 전송 실패")
                # 계정 정지 감지됨인 경우만 중지 (메시지 없는 경우 제외)
                # send_messages_to_groups에서 정지 감지 시 is_running = False 설정됨
                if not self.is_running:
                    self.log(f"⚠️ 계정 정지로 인해 자동전송 중지됨")
            return success
        except Exception as e:
            self.log(f"❌ {pool_name} 계정{account_order} 오류: {e}")
            return False
    
    def create_pool_order(self, pools):
        """풀별 계정 목록 생성 (각 풀 독립적으로 처리)"""
        # 풀별로 계정 목록 분리
        pool_accounts = {}
        if not pools:
            return pool_accounts
            
        for pool_name, accounts in pools.items():
            if accounts:
                pool_accounts[pool_name] = accounts
        
        return pool_accounts
    
    def find_account(self, accounts, phone):
        """계정 찾기"""
        if not accounts:
            return None
            
        if isinstance(accounts, list):
            for account in accounts:
                if account and isinstance(account, dict) and account.get('phone') == phone:
                    return account
        elif isinstance(accounts, dict):
            for account in accounts.values():
                if account and isinstance(account, dict) and account.get('phone') == phone:
                    return account
        return None
    
    def get_account_groups(self, groups, account_phone):
        """계정의 그룹 목록 가져오기 (Firebase에 저장된 순서대로)"""
        account_groups = []
        if not groups or not account_phone:
            return account_groups
            
        if isinstance(groups, dict):
            # account_phone을 키로 사용하여 해당 계정의 데이터 찾기
            account_data = groups.get(account_phone)
            if account_data and isinstance(account_data, dict):
                # selected_groups 가져오기
                selected_groups = account_data.get('selected_groups', [])
                
                # selected_groups가 객체 (딕셔너리)인 경우 리스트로 변환
                if isinstance(selected_groups, dict):
                    # Firebase 객체를 리스트로 변환 (키를 숫자로 정렬, 문자열 "0", "1", "2" 등)
                    sorted_keys = sorted(selected_groups.keys(), key=lambda x: int(x) if x.isdigit() else 999999)
                    selected_groups = [selected_groups[key] for key in sorted_keys]
                
                # selected_groups 리스트에서 각 그룹 정보 가져오기 (순서대로)
                if selected_groups and isinstance(selected_groups, list):
                    for group in selected_groups:
                        if isinstance(group, dict):
                            account_groups.append({
                                'id': group.get('id'),
                                'group_id': group.get('id'),  # id를 group_id로도 설정
                                'title': group.get('title', 'Unknown')
                            })
        return account_groups
    
    def send_messages_to_groups(self, account, groups, messages, group_interval):
        """그룹들에 메시지 전송"""
        try:
            if not self.is_running:
                return False
            
            if not account:
                self.log(f"⚠️ 계정 정보가 없습니다.")
                return False
            
            if not groups:
                self.log(f"⚠️ 그룹 목록이 없습니다.")
                return False
                
            account_messages = self.get_account_messages(messages, account.get('phone'))
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
                error_msg = str(connect_error)
                if "TypeNotFoundError" in error_msg or "76bec211" in error_msg or "Constructor ID" in error_msg:
                    self.log(f"연결 중 프로토콜 오류 (시도 {retry + 1}/{max_retries}) - 무시하고 계속")
                else:
                    self.log(f"연결 실패 (시도 {retry + 1}/{max_retries}): {error_msg}")
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
                
                # 대기 중인 그룹인지 확인
                if group_id in self.group_wait_times:
                    wait_until = self.group_wait_times[group_id]
                    current_time = time.time()
                    if current_time < wait_until:
                        wait_seconds = int(wait_until - current_time)
                        self.log(f"⏸️ 그룹 '{group_title}' 슬로우 모드 대기 중... ({wait_seconds}초 남음)")
                        continue
                    else:
                        # 대기 시간 지남
                        del self.group_wait_times[group_id]
                        self.log(f"✅ 그룹 '{group_title}' 슬로우 모드 해제 - 전송 재개")
                
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
                        error_str = str(e)
                        # FloodWait 에러 처리
                        if "FLOOD_WAIT" in error_str or "flood" in error_str.lower():
                            try:
                                # 에러 메시지에서 대기 시간 추출
                                import re
                                wait_match = re.search(r'(\d+)', error_str)
                                if wait_match:
                                    wait_seconds = int(wait_match.group(1))
                                    # 약간의 여유 시간 추가
                                    wait_until = time.time() + wait_seconds + 5
                                    self.group_wait_times[group_id] = wait_until
                                    self.log(f"⚠️ 그룹 '{group_title}' 슬로우 모드 활성화 - {wait_seconds}초 대기")
                                else:
                                    # 기본 대기 시간 (60초)
                                    wait_until = time.time() + 60
                                    self.group_wait_times[group_id] = wait_until
                                    self.log(f"⚠️ 그룹 '{group_title}' 슬로우 모드 활성화 - 60초 대기")
                            except:
                                # 기본 대기 시간 (60초)
                                wait_until = time.time() + 60
                                self.group_wait_times[group_id] = wait_until
                                self.log(f"⚠️ 그룹 '{group_title}' 슬로우 모드 활성화 - 60초 대기")
                        else:
                            # TypeNotFoundError 등 프로토콜 호환성 오류는 무시
                            if "TypeNotFoundError" in error_str or "Constructor ID" in error_str or "76bec211" in error_str:
                                self.log(f"⚠️ {channel_title} -> {group_title}: 프로토콜 호환성 오류 (무시)")
                            else:
                                self.log(f"❌ 메시지 전달 실패 ({channel_title} -> {group_title}): {str(e)[:100]}")
                            
                            # 계정 정지 감지
                            if any(keyword in error_str.upper() for keyword in ['BANNED', 'RESTRICTED', 'BLOCKED', 'AUTH_KEY_INVALID', 'SESSION_REVOKED']):
                                self.log(f"⚠️ 계정 정지 감지! 자동전송을 즉시 중지합니다.")
                                self.is_running = False
                                return False
                
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
        
        if not messages or not account_phone:
            self.log(f"⚠️ 메시지 또는 계정 전화번호 없음: messages={messages is not None}, phone={account_phone}")
            return account_messages
        
        if isinstance(messages, dict):
            # Firebase의 구조: {랜덤키: {account_phone: "...", selected_messages: [...]}}
            # account_phone으로 데이터 찾기 (랜덤 키 안의 account_phone 필드 검색)
            account_data = None
            for key, data in messages.items():
                if isinstance(data, dict) and data.get('account_phone') == account_phone:
                    account_data = data
                    self.log(f"✅ 계정 {account_phone} 찾음 (키: {key})")
                    break
            
            if not account_data:
                self.log(f"❌ account_phone {account_phone}에 대한 데이터를 찾을 수 없음")
                # 전체 구조 로그
                if messages:
                    sample_keys = list(messages.keys())[:3]
                    self.log(f"📋 메시지 데이터 키 샘플: {sample_keys}")
            
            if account_data and isinstance(account_data, dict):
                # selected_messages 가져오기
                selected_messages = account_data.get('selected_messages', [])
                self.log(f"🔍 selected_messages 타입: {type(selected_messages)}, 값: {selected_messages}")
                
                # selected_messages가 객체 (딕셔너리)인 경우 리스트로 변환
                if isinstance(selected_messages, dict):
                    # Firebase 객체를 리스트로 변환
                    sorted_keys = sorted(selected_messages.keys(), key=lambda x: int(x) if x.isdigit() else 999999)
                    self.log(f"📋 sorted_keys: {sorted_keys}")
                    selected_messages = [selected_messages[key] for key in sorted_keys]
                    self.log(f"📋 selected_messages 변환 완료: {len(selected_messages)}개")
                elif isinstance(selected_messages, list):
                    self.log(f"✅ selected_messages는 이미 리스트: {len(selected_messages)}개")
                
                # selected_messages 리스트에서 각 메시지 정보 가져오기
                if selected_messages and isinstance(selected_messages, list):
                    self.log(f"📋 selected_messages 개수: {len(selected_messages)}")
                    for msg in selected_messages:
                        if isinstance(msg, dict):
                            # Firebase 구조: group_id, id (메시지 ID), group_title
                            source_chat_id = msg.get('group_id')
                            message_id = msg.get('id')  # 메시지 ID
                            group_title = msg.get('group_title', 'Unknown')
                            
                            if source_chat_id and message_id:
                                account_messages.append({
                                    'source_chat_id': source_chat_id,
                                    'message_id': message_id,
                                    'channel_title': group_title
                                })
                    self.log(f"✅ 최종 account_messages 개수: {len(account_messages)}")
                    
                    if len(account_messages) == 0:
                        self.log(f"⚠️ 경고: account_messages가 비어있습니다!")
        
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
    print(f"DEBUG: user_email = {user_email}")
    sys.stdout.flush()
    
    print("DEBUG: AutoSenderDaemon 인스턴스 생성 중...")
    sys.stdout.flush()
    daemon = AutoSenderDaemon(user_email)
    
    print("DEBUG: daemon.run() 호출 중...")
    sys.stdout.flush()
    daemon.run()


if __name__ == "__main__":
    main()

