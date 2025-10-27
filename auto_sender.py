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
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            firebase_url = "https://wint365-date-default-rtdb.asia-southeast1.firebasedatabase.app"
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
            
            # 무한 루프 (절대 중간에 끊기지 않음)
            cycle_count = 0
            while self.is_running:
                # 주기적으로 데이터 다시 로드 (100 사이클마다)
                if cycle_count % 100 == 0:
                    print(f"데이터 새로고침 (사이클: {cycle_count})")
                    settings = self.load_settings()
                    pools = self.load_pools()
                    groups = self.load_groups()
                    messages = self.load_messages()
                    accounts = self.load_accounts()
                    
                    if not all([settings, pools, groups, messages, accounts]):
                        print("데이터 로드 실패, 기존 데이터로 계속 진행")
                    else:
                        # 설정 값 업데이트
                        group_interval = int(settings.get('group_interval_seconds', 10))
                        pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                        print(f"설정 업데이트: 그룹간격={group_interval}초, 풀간격={pool_interval}초")
                        
                        # 새로운 풀 순서 생성
                        pool_order = self.create_pool_order(pools)
                        cycle_count = 0  # 카운터 리셋
                
                # pool_order가 비어있어도 계속 실행
                if not pool_order:
                    print("풀 순서가 비어있습니다. 데이터를 기다립니다...")
                    time.sleep(10)  # 10초 대기 후 다시 시도
                    continue
                
                # 풀별로 구분하여 전송
                previous_pool = None
                for i, pool_info in enumerate(pool_order):
                    if not self.is_running:
                        break
                    
                    pool_name = pool_info['pool_name']
                    account_phone = pool_info['account_phone']
                    
                    # 풀이 바뀌면 풀 간 대기 (풀1 전체 완료 후 풀2 시작 전에 대기)
                    if previous_pool is not None and previous_pool != pool_name:
                        if pool_interval > 0:
                            minutes = pool_interval // 60
                            seconds = pool_interval % 60
                            if minutes > 0:
                                self.log(f"⏳ 풀 간 대기시간: {minutes}분 {seconds}초 남음")
                            else:
                                self.log(f"⏳ 풀 간 대기시간: {seconds}초 남음")
                            
                            # 중지 가능하도록 짧은 단위로 대기
                            waited = 0
                            while waited < pool_interval and self.is_running:
                                time.sleep(1)
                                waited += 1
                                # 남은 시간 로그 (10초마다)
                                if waited % 10 == 0:
                                    remaining = pool_interval - waited
                                    minutes = remaining // 60
                                    seconds = remaining % 60
                                    if minutes > 0:
                                        self.log(f"⏱️ 대기 중... 남은 시간: {minutes}분 {seconds}초")
                                    else:
                                        self.log(f"⏱️ 대기 중... 남은 시간: {seconds}초")
                    
                    self.log(f"📦 풀 {pool_name} 계정 {account_phone} 시작")
                    
                    # 계정 찾기
                    account = self.find_account(accounts, account_phone)
                    if not account:
                        self.log(f"⚠️ 계정 {account_phone}을 찾을 수 없습니다.")
                        previous_pool = pool_name
                        continue
                    
                    # 해당 계정의 그룹 찾기
                    account_groups = self.get_account_groups(groups, account_phone)
                    if not account_groups:
                        self.log(f"⚠️ 계정 {account_phone}의 그룹이 없습니다.")
                        previous_pool = pool_name
                        continue
                    
                    self.log(f"📋 총 {len(account_groups)}개 그룹에 메시지 전송")
                    
                    # 메시지 전송
                    success = self.send_messages_to_groups(
                        account, account_groups, messages, group_interval
                    )
                    
                    if success:
                        self.log(f"✅ 풀 {pool_name} 계정 {account_phone} 완료")
                    else:
                        self.log(f"❌ 풀 {pool_name} 계정 {account_phone} 전송 실패")
                        self.log(f"⚠️ 계정 블락/정지 가능성으로 자동전송 즉시 중단")
                        self.is_running = False
                        break
                    
                    previous_pool = pool_name
                
                cycle_count += 1
                        
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
    
    def create_pool_order(self, pools):
        """풀 전체 계정 완료 방식 순서 생성"""
        pool_order = []
        
        # 각 풀의 모든 계정을 먼저 처리하고 다음 풀로
        for pool_name, accounts in pools.items():
            for account_phone in accounts:
                pool_order.append({
                    'pool_name': pool_name,
                    'account_phone': account_phone
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
                    # selected_groups 배열에서 각 그룹 정보 가져오기
                    selected_groups = group_data.get('selected_groups', [])
                    for group in selected_groups:
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
        
        if isinstance(messages, dict):
            for msg_id, msg_data in messages.items():
                # msg_data가 문자열인 경우 처리
                if isinstance(msg_data, str):
                    continue
                
                if not isinstance(msg_data, dict):
                    continue
                
                if msg_data.get('account_phone') == account_phone:
                    # selected_messages 배열을 가져오기
                    selected_messages = msg_data.get('selected_messages', [])
                    
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

