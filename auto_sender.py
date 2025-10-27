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
        """?�동 ?�송 ?�작"""
        try:
            self.log("?? ?�동?�송 ?�작")
            
            # Firebase?�서 ?�이??가?�오�?            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # ?�이???�락 검�?�??�세 메시지 ?�시
            missing_data = []
            if not settings:
                missing_data.append("???�송 ?�정")
            if not pools:
                missing_data.append("???� ?�택")
            if not groups:
                missing_data.append("??그룹 ?�택")
            if not messages:
                missing_data.append("??메시지 ?�택")
            if not accounts:
                missing_data.append("??계정 ?�이??)
            
            if missing_data:
                missing_list = "\n".join(missing_data)
                messagebox.showerror(
                    "?�이???�락", 
                    f"?�동 ?�송???�작?�려�??�음 ?�이?��? ?�요?�니??\n\n{missing_list}\n\n"
                    f"�?메뉴?�서 ?�이?��? ?�정?�주?�요."
                )
                # ?�류 발생 ??버튼 ?�태 초기??                if self.status_callback:
                    self.parent.after(0, lambda: self.status_callback(False))
                return
            
            # ?�동?�송 ?�작 (?�인 ?�이 바로 ?�작)
            self.is_running = True
            
            # ?�태 콜백 ?�출
            if self.status_callback:
                self.parent.after(0, lambda: self.status_callback(True))
            
            # 백그?�운?�에???�행
            thread = threading.Thread(target=self.run_auto_send, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"???�동?�송 ?�작 ?�류: {str(e)}")
            messagebox.showerror("?�류", f"?�동 ?�송 ?�작 �??�류: {str(e)}")
            # ?�류 발생 ??버튼 ?�태 초기??            if self.status_callback:
                self.parent.after(0, lambda: self.status_callback(False))
    
    def load_settings(self):
        """?�송 ?�정 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            settings_url = f"{firebase_url}/users/{self.user_email}/time_settings.json"
            
            response = requests.get(settings_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"?�정 로드 ?�류: {e}")
        return None
    
    def load_pools(self):
        """?� ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            pools_url = f"{firebase_url}/users/{self.user_email}/pools.json"
            
            response = requests.get(pools_url)
            if response.status_code == 200:
                data = response.json()
                if data and 'pools' in data:
                    return data['pools']
        except Exception as e:
            print(f"?� 로드 ?�류: {e}")
        return None
    
    def load_groups(self):
        """그룹 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            groups_url = f"{firebase_url}/users/{self.user_email}/group_selections.json"
            
            response = requests.get(groups_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"그룹 로드 ?�류: {e}")
        return None
    
    def load_messages(self):
        """메시지 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            messages_url = f"{firebase_url}/users/{self.user_email}/forward_messages.json"
            
            response = requests.get(messages_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"메시지 로드 ?�류: {e}")
        return None
    
    def load_accounts(self):
        """계정 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            accounts_url = f"{firebase_url}/users/{self.user_email}/selected_accounts.json"
            
            response = requests.get(accounts_url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"계정 로드 ?�류: {e}")
        return None
    
    def run_auto_send(self):
        """?�동 ?�송 ?�행"""
        try:
            # ?�이???�시 로드
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 초기 ?�정
            group_interval = 10  # 기본�?            pool_interval = 300  # 기본�?(5�?
            pool_order = []
            
            # 초기 ?�이???�인
            if not all([settings, pools, groups, messages, accounts]):
                print("초기 ?�이?��? ?�습?�다. ?�이?��? 기다립니??..")
            else:
                group_interval = int(settings.get('group_interval_seconds', 10))
                pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                pool_order = self.create_pool_order(pools)
            
            # 무한 루프 (?��? 중간???�기지 ?�음)
            cycle_count = 0
            while self.is_running:
                # 주기?�으�??�이???�시 로드 (100 ?�이?�마??
                if cycle_count % 100 == 0:
                    print(f"?�이???�로고침 (?�이?? {cycle_count})")
                    settings = self.load_settings()
                    pools = self.load_pools()
                    groups = self.load_groups()
                    messages = self.load_messages()
                    accounts = self.load_accounts()
                    
                    if not all([settings, pools, groups, messages, accounts]):
                        print("?�이??로드 ?�패, 기존 ?�이?�로 계속 진행")
                    else:
                        # ?�정 �??�데?�트
                        group_interval = int(settings.get('group_interval_seconds', 10))
                        pool_interval = int(settings.get('pool_interval_minutes', 5)) * 60
                        print(f"?�정 ?�데?�트: 그룹간격={group_interval}�? ?�간격={pool_interval}�?)
                        
                        # ?�로???� ?�서 ?�성
                        pool_order = self.create_pool_order(pools)
                        cycle_count = 0  # 카운??리셋
                
                # pool_order가 비어?�어??계속 ?�행
                if not pool_order:
                    print("?� ?�서가 비어?�습?�다. ?�이?��? 기다립니??..")
                    time.sleep(10)  # 10�??��????�시 ?�도
                    continue
                
                # ?�별로 구분?�여 ?�송
                previous_pool = None
                for i, pool_info in enumerate(pool_order):
                    if not self.is_running:
                        break
                    
                    pool_name = pool_info['pool_name']
                    account_phone = pool_info['account_phone']
                    
                    # ?�??바뀌면 ?� �??��?(?�1 ?�체 ?�료 ???�2 ?�작 ?�에 ?��?
                    if previous_pool is not None and previous_pool != pool_name:
                        if pool_interval > 0:
                            minutes = pool_interval // 60
                            seconds = pool_interval % 60
                            if minutes > 0:
                                self.log(f"???� �??�기시�? {minutes}�?{seconds}�??�음")
                            else:
                                self.log(f"???� �??�기시�? {seconds}�??�음")
                            
                            # 중�? 가?�하?�록 짧�? ?�위�??��?                            waited = 0
                            while waited < pool_interval and self.is_running:
                                time.sleep(1)
                                waited += 1
                                # ?��? ?�간 로그 (10초마??
                                if waited % 10 == 0:
                                    remaining = pool_interval - waited
                                    minutes = remaining // 60
                                    seconds = remaining % 60
                                    if minutes > 0:
                                        self.log(f"?�️ ?��?�?.. ?��? ?�간: {minutes}�?{seconds}�?)
                                    else:
                                        self.log(f"?�️ ?��?�?.. ?��? ?�간: {seconds}�?)
                    
                    self.log(f"?�� ?� {pool_name} 계정 {account_phone} ?�작")
                    
                    # 계정 찾기
                    account = self.find_account(accounts, account_phone)
                    if not account:
                        self.log(f"?�️ 계정 {account_phone}??찾을 ???�습?�다.")
                        previous_pool = pool_name
                        continue
                    
                    # ?�당 계정??그룹 찾기
                    account_groups = self.get_account_groups(groups, account_phone)
                    if not account_groups:
                        self.log(f"?�️ 계정 {account_phone}??그룹???�습?�다.")
                        previous_pool = pool_name
                        continue
                    
                    self.log(f"?�� �?{len(account_groups)}�?그룹??메시지 ?�송")
                    
                    # 메시지 ?�송
                    success = self.send_messages_to_groups(
                        account, account_groups, messages, group_interval
                    )
                    
                    if success:
                        self.log(f"???� {pool_name} 계정 {account_phone} ?�료")
                    else:
                        self.log(f"???� {pool_name} 계정 {account_phone} ?�송 ?�패")
                        self.log(f"?�️ 계정 블락/?��? 가?�성?�로 ?�동?�송 즉시 중단")
                        self.is_running = False
                        break
                    
                    previous_pool = pool_name
                
                cycle_count += 1
                        
        except Exception as e:
            print(f"?�동 ?�송 ?�류: {e}")
            import traceback
            traceback.print_exc()
            # ?�류가 발생?�도 계속 ?�행 (중�? 버튼?�로�?종료)
            print("?�류 발생?��?�?계속 ?�행?�니??..")
            # ?�류 발생 ??버튼 ?�태???��? (계속 ?�송 �??�태)
        finally:
            # ?�송???�상 종료??경우?�만 ?�시 ?�일 ?�리
            if not self.is_running:
                # 로그??출력?��? ?�고 바로 ?�리�?(??방�?)
                try:
                    self.cleanup_temp_files()
                except:
                    pass
                # ?�태 콜백?� ?��? stop_auto_send?�서 ?�출??    
    def create_pool_order(self, pools):
        """?� ?�체 계정 ?�료 방식 ?�서 ?�성"""
        pool_order = []
        
        # �??�??모든 계정??먼�? 처리?�고 ?�음 ?��?        for pool_name, accounts in pools.items():
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
        """계정??그룹 목록 가?�오�?""
        account_groups = []
        if isinstance(groups, dict):
            for group_id, group_data in groups.items():
                if group_data.get('account_phone') == account_phone:
                    # selected_groups 배열?�서 �?그룹 ?�보 가?�오�?                    selected_groups = group_data.get('selected_groups', [])
                    for group in selected_groups:
                        account_groups.append({
                            'id': group.get('id'),
                            'group_id': group.get('id'),  # id�?group_id로도 ?�정
                            'title': group.get('title', 'Unknown')
                        })
        return account_groups
    
    def send_messages_to_groups(self, account, groups, messages, group_interval):
        """그룹?�에 메시지 ?�송"""
        try:
            # 중�? ?�호 체크
            if not self.is_running:
                return False
            
            # 계정??메시지 찾기
            account_messages = self.get_account_messages(messages, account['phone'])
            if not account_messages:
                print(f"계정 {account.get('phone')}???�??메시지가 ?�습?�다.")
                return False
            
            # 중�? ?�호 체크
            if not self.is_running:
                return False
            
            # ?�레그램 ?�라?�언???�성
            session_data = base64.b64decode(account['sessionData'])
            temp_session = tempfile.NamedTemporaryFile(delete=False, suffix='.session')
            temp_session.write(session_data)
            temp_session.close()
            self.temp_files.append(temp_session.name)
            
            api_id = account['apiId']
            api_hash = account['apiHash']
            
            # 비동기로 ?�송
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self.send_messages_async(
                        temp_session.name, api_id, api_hash, 
                        groups, account_messages, group_interval
                    )
                )
                
                # 메시지 ?�송 ???�션 갱신
                if success:
                    try:
                        print(f"?�션 갱신 �? {account.get('phone')}")
                        refresh_session_now(account)
                        print(f"?�션 갱신 ?�료: {account.get('phone')}")
                    except Exception as session_error:
                        print(f"?�션 갱신 ?�류: {session_error}")
                
                return success
            finally:
                loop.close()
                
        except Exception as e:
            print(f"메시지 ?�송 ?�류: {e}")
            import traceback
            traceback.print_exc()
            # ?�류가 발생?�도 계속 진행
            return True
    
    async def send_messages_async(self, session_path, api_id, api_hash, groups, messages, group_interval):
        """비동기로 메시지 ?�송"""
        client = TelegramClient(session_path, api_id, api_hash)
        max_retries = 3  # 최�? ?�시???�수
        
        for retry in range(max_retries):
            try:
                # ?�결 ?�도
                await client.connect()
                print(f"?�레그램 ?�결 ?�공 (?�도 {retry + 1}/{max_retries})")
                break
            except Exception as connect_error:
                print(f"?�결 ?�패 (?�도 {retry + 1}/{max_retries}): {connect_error}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)  # 5�??��????�시??                else:
                    print("최�? ?�시???�수 초과, ?�음 계정?�로 ?�동")
                    return False
        
        try:
            for group_info in groups:
                if not self.is_running:
                    break
                
                group_id = group_info.get('group_id')
                group_title = group_info.get('title', 'Unknown')
                
                if not group_id:
                    continue
                
                # �?메시지 ?�달
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
                        # ?�본 그�?�??�달 (미디???�함)
                        source_peer = await client.get_entity(source_chat_id)
                        target_peer = await client.get_entity(group_id)
                        
                        # ?�달 방식?�로 메시지 보내�?                        await client.forward_messages(
                            entity=target_peer,
                            messages=[message_id],
                            from_peer=source_peer
                        )
                        
                        message_count += 1
                        print(f"??메시지 ?�달 ?�공: {channel_title} -> {group_title}")
                        
                    except Exception as e:
                        print(f"??메시지 ?�달 ?�패 ({channel_title} -> {group_title}): {e}")
                
                # 그룹 ?�체 ?�송 ?�료 로그
                if message_count > 0:
                    self.log(f"??그룹 '{group_title}'??{message_count}�?메시지 ?�송 ?�공")
                
                # 그룹 �?간격 ?��?                if group_interval > 0:
                    self.log(f"???�음 그룹 ?�송 ?�기시�? {group_interval}�?)
                    waited = 0
                    while waited < group_interval and self.is_running:
                        await asyncio.sleep(1)
                        waited += 1
                else:
                    self.log(f"???�음 그룹?�로 ?�동...")
            
            await client.disconnect()
            return True
            
        except Exception as e:
            try:
                await client.disconnect()
            except:
                pass
            print(f"?�송 ?�류: {e}")
            return False
    
    def get_account_messages(self, messages, account_phone):
        """계정??메시지 목록 가?�오�?""
        account_messages = []
        
        if isinstance(messages, dict):
            for msg_id, msg_data in messages.items():
                # msg_data가 문자?�인 경우 처리
                if isinstance(msg_data, str):
                    continue
                
                if not isinstance(msg_data, dict):
                    continue
                
                if msg_data.get('account_phone') == account_phone:
                    # selected_messages 배열??가?�오�?                    selected_messages = msg_data.get('selected_messages', [])
                    
                    # �?메시지???�???�보 구성
                    for msg in selected_messages:
                        # msg가 ?�셔?�리가 ?�닌 경우 건너?�기
                        if not isinstance(msg, dict):
                            continue
                        
                        # group_id�?source_chat_id�??�용
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
        """?�시 ?�일 ?�리"""
        for temp_file in self.temp_files:
            try:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"?�일 ??�� ?�류: {e}")
        self.temp_files = []
    
    def stop_auto_send(self):
        """?�동 ?�송 중�? - 즉시 중�? ?�청"""
        # 즉시 중�? ?�래그만 ?�정 (???�이 빠르�?
        self.is_running = False
        
        # 로그?� ?�리??백그?�운?�에??처리
        def cleanup_async():
            try:
                self.log("?�� ?�동?�송 중�? ?�청")
                self.cleanup_temp_files()
            except:
                pass
        
        # 백그?�운?�에???�리 ?�업 ?�행
        threading.Thread(target=cleanup_async, daemon=True).start()
        
        # ?�태 콜백 즉시 ?�출 (UI ?�데?�트)
        if self.status_callback:
            self.parent.after(0, lambda: self.status_callback(False))


