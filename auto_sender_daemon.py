#!/usr/bin/env python3
"""
백그?�운???�동?�송 ?�몬
Render?�서 ?�행?�어 PC?� 무�??�게 계속 ?�행??"""
import sys
import time
import requests
import asyncio
import base64
import tempfile
from telethon import TelegramClient
from datetime import datetime
import warnings
import logging

# Telethon TypeNotFoundError 경고 ?�전 무시
warnings.filterwarnings('ignore', category=UserWarning, module='telethon')

# Telethon 로깅 차단
logging.getLogger('telethon').setLevel(logging.CRITICAL)
logging.getLogger('telethon.session').setLevel(logging.CRITICAL)
logging.getLogger('telethon.network.mtprotosender').setLevel(logging.CRITICAL)

# ?�역 ?�외 ?�들?�로 TypeNotFoundError 무시
import sys
def custom_excepthook(exc_type, exc_value, exc_traceback):
    if 'TypeNotFoundError' in str(exc_type) or 'Could not find a matching Constructor ID' in str(exc_value):
        return  # ?�전 무시
    # �??�의 ?�류???�래?��?출력
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = custom_excepthook

# 즉시 출력
print("=" * 60)
print("?? auto_sender_daemon.py ?�작")
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
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        sys.stdout.flush()
        
    def check_firebase_status(self):
        """DMA?�서 ?�동?�송 ?�태 ?�인"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            status_url = f"{firebase_url}/users/{self.user_email}/auto_send_status.json"
            
            response = requests.get(status_url, timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                return status_data and status_data.get('is_running', False)
        except Exception as e:
            self.log(f"?�태 ?�인 ?�류: {e}")
        return False
    
    def load_settings(self):
        """?�송 ?�정 로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            settings_url = f"{firebase_url}/users/{self.user_email}/time_settings.json"
            
            response = requests.get(settings_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"?�정 로드 ?�류: {e}")
        return None
    
    def load_pools(self):
        """?� ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            pools_url = f"{firebase_url}/users/{self.user_email}/pools.json"
            
            response = requests.get(pools_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'pools' in data:
                    return data['pools']
        except Exception as e:
            self.log(f"?� 로드 ?�류: {e}")
        return None
    
    def load_groups(self):
        """그룹 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            groups_url = f"{firebase_url}/users/{self.user_email}/group_selections.json"
            
            response = requests.get(groups_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"그룹 로드 ?�류: {e}")
        return None
    
    def load_messages(self):
        """메시지 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            messages_url = f"{firebase_url}/users/{self.user_email}/forward_messages.json"
            
            response = requests.get(messages_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"메시지 로드 ?�류: {e}")
        return None
    
    def load_accounts(self):
        """계정 ?�이??로드"""
        try:
            firebase_url = "https://wint24-62cd2-default-rtdb.asia-southeast1.firebasedatabase.app"
            accounts_url = f"{firebase_url}/users/{self.user_email}/selected_accounts.json"
            
            response = requests.get(accounts_url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"계정 로드 ?�류: {e}")
        return None
    
    def run(self):
        """?�몬 메인 루프"""
        self.log("=" * 60)
        self.log("?? ?�동?�송 ?�몬 ?�작")
        self.log(f"?�용?? {self.user_email}")
        self.log("=" * 60)
        
        # 무한 루프 - DMA ?�태 ?�인
        while True:
            try:
                # DMA?�서 ?�태 ?�인
                should_run = self.check_firebase_status()
                
                if should_run and not self.is_running:
                    # ?�작
                    self.log("?�� DMA ?�태: ON - ?�동?�송 ?�작")
                    self.is_running = True
                    # 별도 ?�레?�에???�행
                    import threading
                    thread = threading.Thread(target=self.run_auto_send, daemon=True)
                    thread.start()
                elif not should_run and self.is_running:
                    # 중�?
                    self.log("?�� DMA ?�태: OFF - ?�동?�송 중�?")
                    self.is_running = False
                
                # 5분마???�태 ?�인 (Firebase ?�용???�??줄이�?
                time.sleep(300)
                
            except KeyboardInterrupt:
                self.log("중�? ?�호 ?�신 - 종료")
                self.is_running = False
                break
            except Exception as e:
                self.log(f"?�몬 ?�류: {e}")
                time.sleep(10)  # ?�류 ??10�??��?    
    def run_auto_send(self):
        """?�동 ?�송 ?�행"""
        try:
            # ?�이??로드
            settings = self.load_settings()
            pools = self.load_pools()
            groups = self.load_groups()
            messages = self.load_messages()
            accounts = self.load_accounts()
            
            # 초기 ?�정
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
                # DMA ?�태 계속 ?�인 (30초마?�만)
                if cycle_count % 30 == 0:
                    if not self.check_firebase_status():
                        self.log("DMA?�서 OFF ?�호 받음 - 중�?")
                        self.is_running = False
                        break
                
                # ?�이???�로고침 (1000 ?�이?�마??- Firebase ?�용???�??줄이�?
                if cycle_count % 1000 == 0:
                    self.log(f"?�이???�로고침 (?�이?? {cycle_count})")
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
                    self.log("?� ?�서가 비어?�습?�다. ?�이???��?�?..")
                    time.sleep(10)
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
                    
                    account = self.find_account(accounts, account_phone)
                    if not account:
                        self.log(f"?�️ 계정 {account_phone}??찾을 ???�습?�다.")
                        previous_pool = pool_name
                        continue
                    
                    account_groups = self.get_account_groups(groups, account_phone)
                    if not account_groups:
                        self.log(f"?�️ 계정 {account_phone}??그룹???�습?�다.")
                        previous_pool = pool_name
                        continue
                    
                    self.log(f"?�� �?{len(account_groups)}�?그룹??메시지 ?�송")
                    
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
            self.log(f"?�동 ?�송 ?�류: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
    
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
                if account is not None and isinstance(account, dict) and account.get('phone') == phone:
                    return account
        elif isinstance(accounts, dict):
            for account in accounts.values():
                if account is not None and isinstance(account, dict) and account.get('phone') == phone:
                    return account
        return None
    
    def get_account_groups(self, groups, account_phone):
        """계정??그룹 목록 가?�오�?""
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
        """그룹?�에 메시지 ?�송"""
        try:
            if not self.is_running:
                return False
            
            account_messages = self.get_account_messages(messages, account['phone'])
            if not account_messages:
                self.log(f"계정 {account.get('phone')}???�??메시지가 ?�습?�다.")
                return False
            
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
                return success
            finally:
                loop.close()
                
        except Exception as e:
            self.log(f"메시지 ?�송 ?�류: {e}")
            import traceback
            traceback.print_exc()
            return True
    
    async def send_messages_async(self, session_path, api_id, api_hash, groups, messages, group_interval):
        """비동기로 메시지 ?�송"""
        client = TelegramClient(session_path, api_id, api_hash)
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                await client.connect()
                self.log(f"?�레그램 ?�결 ?�공 (?�도 {retry + 1}/{max_retries})")
                break
            except Exception as connect_error:
                self.log(f"?�결 ?�패 (?�도 {retry + 1}/{max_retries}): {connect_error}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return False
        
        try:
            # 근본 ?�인: client.connect() ??Telethon???�동?�로 백그?�운?�에??메시지�??�신??            # 계정??가?�한 그룹?�서 ??메시지가 ?�어?�면 ?�동?�로 ?�싱 ?�도
            # ??메시지 ?�?�을 ?�식 못하�?TypeNotFoundError 발생 (?�순 경고, ?�송?�는 ?�향 ?�음)
            
            for group_info in groups:
                if not self.is_running:
                    break
                
                group_id = group_info.get('group_id')
                group_title = group_info.get('title', 'Unknown')
                
                if not group_id:
                    continue
                
                # ?��?중인 그룹?��? ?�인
                if group_id in self.group_wait_times:
                    wait_until = self.group_wait_times[group_id]
                    current_time = time.time()
                    if current_time < wait_until:
                        wait_seconds = int(wait_until - current_time)
                        self.log(f"?�️ 그룹 '{group_title}' ?�로??모드 ?��?�?.. ({wait_seconds}�??�음)")
                        continue
                    else:
                        # ?��??�간 지??                        del self.group_wait_times[group_id]
                        self.log(f"??그룹 '{group_title}' ?�로??모드 ?�제 - ?�송 ?�개")
                
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
                        self.log(f"??메시지 ?�달 ?�공: {channel_title} -> {group_title}")
                        
                    except Exception as e:
                        # 무시?�도 ?�는 ?�류??(?��?지/비디???�함 메시지???�상 ?�송??
                        if "TypeNotFoundError" in str(type(e).__name__):
                            message_count += 1
                            self.log(f"?�️ 메시지 ?�달 경고 (무시??: {str(e)[:50]}")
                            continue
                        error_str = str(e)
                        # FloodWait ?�러 처리
                        if "FLOOD_WAIT" in error_str or "flood" in error_str.lower():
                            try:
                                # ?�러 메시지?�서 ?��??�간 추출
                                import re
                                wait_match = re.search(r'(\d+)', error_str)
                                if wait_match:
                                    wait_seconds = int(wait_match.group(1))
                                    # ?�간???�유 ?�간 추�?
                                    wait_until = time.time() + wait_seconds + 5
                                    self.group_wait_times[group_id] = wait_until
                                    self.log(f"?�️ 그룹 '{group_title}' ?�로??모드 ?�성??- {wait_seconds}�??��?)
                                else:
                                    # 기본 ?��??�간 (60�?
                                    wait_until = time.time() + 60
                                    self.group_wait_times[group_id] = wait_until
                                    self.log(f"?�️ 그룹 '{group_title}' ?�로??모드 ?�성??- 60�??��?)
                            except:
                                # 기본 ?��??�간 (60�?
                                wait_until = time.time() + 60
                                self.group_wait_times[group_id] = wait_until
                                self.log(f"?�️ 그룹 '{group_title}' ?�로??모드 ?�성??- 60�??��?)
                        else:
                            self.log(f"??메시지 ?�달 ?�패 ({channel_title} -> {group_title}): {e}")
                
                if message_count > 0:
                    self.log(f"??그룹 '{group_title}'??{message_count}�?메시지 ?�송 ?�공")
                
                if group_interval > 0:
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
            self.log(f"?�송 ?�류: {e}")
            return False
    
    def get_account_messages(self, messages, account_phone):
        """계정??메시지 목록 가?�오�?""
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
        """?�시 ?�일 ?�리"""
        for temp_file in self.temp_files:
            try:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                self.log(f"?�일 ??�� ?�류: {e}")
        self.temp_files = []


def main():
    """메인 ?�수"""
    # ?�용???�메???�인
    if len(sys.argv) < 2:
        print("?�용�? python auto_sender_daemon.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    print(f"DEBUG: user_email = {user_email}")
    sys.stdout.flush()
    
    print("DEBUG: AutoSenderDaemon ?�스?�스 ?�성 �?..")
    sys.stdout.flush()
    daemon = AutoSenderDaemon(user_email)
    
    print("DEBUG: daemon.run() ?�출 �?..")
    sys.stdout.flush()
    daemon.run()


if __name__ == "__main__":
    main()


