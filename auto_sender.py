import tkinter as tk
from tkinter import messagebox
import requests
import asyncio
import threading
import base64
import tempfile
from telethon import TelegramClient
import time
from session_manager import refresh_session_now

class AutoSender:
    def __init__(self, parent_window, user_email, status_callback=None, log_callback=None):
        self.parent = parent_window
        self.user_email = user_email
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.is_running = False
        self.temp_files = []
        
    def log(self, message):
        """로그 출력"""
        print(message)
        if self.log_callback:
            self.parent.after(0, lambda: self.log_callback(message))
        
    def start_auto_send(self):
        """자동 전송 시작"""
        try:
            self.log("🚀 자동전송 시작")
            
            # Firebase에서 데이터 가져오기
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 데이터 누락 검증 및 상세 메시지 표시
            missing_data = []
            if not settings:
                missing_data.append("• 전송 설정")
            if not pools:
                missing_data.append("• 풀 선택")
            if not groups:
                missing_data.append("• 그룹 선택")
            if not messages:
                missing_data.append("• 메시지 선택")
            if not accounts:
                missing_data.append("• 계정 데이터")
            
            if missing_data:
                missing_list = "\n".join(missing_data)
                messagebox.showerror(
                    "데이터 누락", 
                    f"자동 전송을 시작하려면 다음 데이터가 필요합니다:\n\n{missing_list}\n\n"
                    f"각 메뉴에서 데이터를 설정해주세요."
                )
                # 오류 발생 시 버튼 상태 초기화
                if self.status_callback:
                    self.parent.after(0, lambda: self.status_callback(False))
                return
            
            # 자동전송 시작 (확인 없이 바로 시작)
            self.is_running = True
            
            # 상태 콜백 호출
            if self.status_callback:
                self.parent.after(0, lambda: self.status_callback(True))
            
            # 백그라운드에서 실행
            thread = threading.Thread(target=self.run_auto_send, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"❌ 자동전송 시작 오류: {str(e)}")
            messagebox.showerror("오류", f"자동 전송 시작 중 오류: {str(e)}")
            # 오류 발생 시 버튼 상태 초기화
            if self.status_callback:
                self.parent.after(0, lambda: self.status_callback(False))
    
    def load_settings(self):
        """전송 설정 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            settings_url = f"{firebase_url}/users/{self.user_email}/time_settings.json"
            
            response = requests.get(settings_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"설정 로드 오류: {e}")
        return None
    
    def load_pools(self):
        """풀 데이터 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            pools_url = f"{firebase_url}/users/{self.user_email}/pools.json"
            
            response = requests.get(pools_url)
            if response.status_code == 200:
                data = response.json()
                if data and 'pools' in data:
                    return data['pools']
        except Exception as e:
            print(f"풀 로드 오류: {e}")
        return None
    
    def load_groups(self):
        """그룹 데이터 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            groups_url = f"{firebase_url}/users/{self.user_email}/group_selections.json"
            
            response = requests.get(groups_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"그룹 로드 오류: {e}")
        return None
    
    def load_messages(self):
        """메시지 데이터 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            messages_url = f"{firebase_url}/users/{self.user_email}/forward_messages.json"
            
            response = requests.get(messages_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"메시지 로드 오류: {e}")
        return None
    
    def load_accounts(self):
        """계정 데이터 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            accounts_url = f"{firebase_url}/users/{self.user_email}/selected_accounts.json"
            
            response = requests.get(accounts_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"계정 로드 오류: {e}")
        return None
    
    def run_auto_send(self):
        """자동 전송 실행"""
        try:
            # 데이터 다시 로드
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 초기 설정
            group_interval = 10  # 기본값
            pool_interval = 300  # 기본값 (5분)
            pool_order = []
            
            # 초기 데이터 확인
            if not all([settings, pools, groups, messages, accounts]):
                print("초기 데이터가 없습니다. 데이터를 기다립니다...")
            else:
                group_interval = int(settings.get('group_interval_seconds', 10))
                pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                pool_order = self.create_pool_order(pools)
            
            # 각 풀을 독립적으로 무한 루프로 실행
            pool_threads = []
            for idx, (pool_name, pool_accounts) in enumerate(pool_order.items()):
                # 각 풀을 별도 스레드로 실행
                thread = threading.Thread(
                    target=self.run_pool_cycle,
                    args=(pool_name, pool_accounts, idx * pool_interval, accounts, groups, messages, group_interval),
                    daemon=True
                )
                thread.start()
                pool_threads.append(thread)
            
            # 모든 풀이 중지될 때까지 대기
            while self.is_running:
                time.sleep(1)
                        
        except Exception as e:
            print(f"자동 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류가 발생해도 계속 실행 (중지 버튼으로만 종료)
            print("오류 발생했지만 계속 실행합니다...")
            # 오류 발생 시 버튼 상태는 유지 (계속 전송 중 상태)
        finally:
            # 전송이 정상 종료된 경우에만 임시 파일 정리
            if not self.is_running:
                # 로그는 출력하지 않고 바로 정리만 (렉 방지)
                try:
                    self.cleanup_temp_files()
                except:
                    pass
                # 상태 콜백은 이미 stop_auto_send에서 호출됨
    
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
        # 패턴: 계정 1,2,3,4 (4개)일 때
        # Group 0: [0] - 계정1
        # Group 1: [1, 2] - 계정2,3 (동시)
        # Group 2: [3, 0] - 계정4와 계정1 (동시)
        # Group 3: [1, 2] - 계정2,3 (동시)
        # Group 4: [3, 0] - 계정4와 계정1 (동시)
        # ... 반복
        
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
                account_data = pool_accounts[idx]
                
                if isinstance(account_data, dict):
                    account_phone = account_data.get('account', account_data)
                else:
                    account_phone = account_data
                
                account = self.find_account(accounts, account_phone)
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
    
    def create_pool_order(self, pools):
        """풀별 계정 목록 생성 (각 풀 독립적으로 처리)"""
        # 풀별로 계정 목록 분리
        pool_accounts = {}
        for pool_name, accounts in pools.items():
            pool_accounts[pool_name] = accounts
        
        return pool_accounts
    
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
        """계정의 그룹 목록 가져오기 (Firebase에 저장된 순서대로)"""
        account_groups = []
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
                    print(f"[DEBUG] selected_groups keys: {sorted_keys}")
                elif not isinstance(selected_groups, list):
                    selected_groups = []
                
                # selected_groups 리스트에서 각 그룹 정보 가져오기 (순서대로)
                if selected_groups:
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
            # 중지 신호 체크
            if not self.is_running:
                return False
            
            # 계정의 메시지 찾기
            account_messages = self.get_account_messages(messages, account['phone'])
            if not account_messages:
                print(f"계정 {account.get('phone')}에 대한 메시지가 없습니다.")
                return False
            
            # 중지 신호 체크
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
                
                # 메시지 전송 후 세션 갱신
                if success:
                    try:
                        print(f"세션 갱신 중: {account.get('phone')}")
                        refresh_session_now(account)
                        print(f"세션 갱신 완료: {account.get('phone')}")
                    except Exception as session_error:
                        print(f"세션 갱신 오류: {session_error}")
                
                return success
            finally:
                loop.close()
                
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류가 발생해도 계속 진행
            return True
    
    async def send_messages_async(self, session_path, api_id, api_hash, groups, messages, group_interval):
        """비동기로 메시지 전송"""
        client = TelegramClient(session_path, api_id, api_hash)
        max_retries = 3  # 최대 재시도 횟수
        
        for retry in range(max_retries):
            try:
                # 연결 시도
                await client.connect()
                print(f"텔레그램 연결 성공 (시도 {retry + 1}/{max_retries})")
                break
            except Exception as connect_error:
                print(f"연결 실패 (시도 {retry + 1}/{max_retries}): {connect_error}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)  # 5초 대기 후 재시도
                else:
                    print("최대 재시도 횟수 초과, 다음 계정으로 이동")
                    return False
        
        try:
            for group_info in groups:
                if not self.is_running:
                    break
                
                group_id = group_info.get('group_id')
                group_title = group_info.get('title', 'Unknown')
                
                if not group_id:
                    continue
                
                # 각 메시지 전달
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
                        # 원본 그대로 전달 (미디어 포함)
                        source_peer = await client.get_entity(source_chat_id)
                        target_peer = await client.get_entity(group_id)
                        
                        # 전달 방식으로 메시지 보내기
                        await client.forward_messages(
                            entity=target_peer,
                            messages=[message_id],
                            from_peer=source_peer
                        )
                        
                        message_count += 1
                        print(f"✅ 메시지 전달 성공: {channel_title} -> {group_title}")
                        
                    except Exception as e:
                        print(f"❌ 메시지 전달 실패 ({channel_title} -> {group_title}): {e}")
                
                # 그룹 전체 전송 완료 로그
                if message_count > 0:
                    self.log(f"✅ 그룹 '{group_title}'에 {message_count}개 메시지 전송 성공")
                
                # 그룹 간 간격 대기
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
            print(f"전송 오류: {e}")
            return False
    
    def get_account_messages(self, messages, account_phone):
        """계정의 메시지 목록 가져오기"""
        account_messages = []
        
        # 계정 전화번호 정규화
        phone_key = account_phone.replace('+', '').replace(' ', '').replace('-', '')
        
        if isinstance(messages, dict):
            # 모든 항목을 순회하면서 account_phone으로 필터링
            for key, data in messages.items():
                if isinstance(data, dict) and data.get('account_phone', '').replace('+', '').replace(' ', '').replace('-', '') == phone_key:
                    # selected_messages 배열을 가져오기
                    selected_messages = data.get('selected_messages', [])
                    
                    # 각 메시지에 대한 정보 구성
                    for msg in selected_messages:
                        # msg가 딕셔너리가 아닌 경우 건너뛰기
                        if not isinstance(msg, dict):
                            continue
                        
                        # group_id를 source_chat_id로 사용
                        source_chat_id = msg.get('group_id')
                        message_id = msg.get('id')
                        group_title = msg.get('group_title', 'Unknown')
                        
                        if source_chat_id and message_id:
                            account_messages.append({
                                'source_chat_id': source_chat_id,
                                'message_id': message_id,
                                'channel_title': group_title
                            })
                    break
        
        return account_messages
    
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        for temp_file in self.temp_files:
            try:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"파일 삭제 오류: {e}")
        self.temp_files = []
    
    def stop_auto_send(self):
        """자동 전송 중지 - 즉시 중지 요청"""
        # 즉시 중지 플래그만 설정 (렉 없이 빠르게)
        self.is_running = False
        
        # 로그와 정리는 백그라운드에서 처리
        def cleanup_async():
            try:
                self.log("🛑 자동전송 중지 요청")
                self.cleanup_temp_files()
            except:
                pass
        
        # 백그라운드에서 정리 작업 실행
        threading.Thread(target=cleanup_async, daemon=True).start()
        
        # 상태 콜백 즉시 호출 (UI 업데이트)
        if self.status_callback:
            self.parent.after(0, lambda: self.status_callback(False))

