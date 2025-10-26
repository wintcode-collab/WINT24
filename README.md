# Render 배포 파일

## 📦 이 폴더의 파일들

이 폴더에 있는 파일들을 그대로 GitHub에 업로드하면 됩니다.

## 📋 파일 목록

1. **auto_sender_daemon.py** - 백그라운드 자동전송 데몬
2. **auto_sender.py** - 자동전송 로직
3. **session_manager.py** - 세션 관리
4. **requirements.txt** - Python 의존성
5. **render.yaml** - Render 설정
6. **.gitignore** - Git 제외 설정
7. **README.md** - 이 파일

## 🚀 배포 방법

### 방법 1: GitHub 웹사이트에서 직접 업로드
1. https://github.com/wintcode-collab/WINT24 접속
2. "Add file" → "Upload files" 클릭
3. 이 폴더의 모든 파일 드래그 앤 드롭
4. "Commit changes" 클릭

### 방법 2: GitHub Desktop 사용
1. GitHub Desktop 설치: https://desktop.github.com/
2. "Clone a repository from the Internet" 선택
3. URL: `https://github.com/wintcode-collab/WINT24.git`
4. Local path: 원하는 위치 (예: `C:\deploy`)
5. Clone 클릭
6. `render_deploy` 폴더의 파일들을 복사해서 붙여넣기
7. "Commit to main" 클릭
8. "Push origin" 클릭

## ⚙️ Render 설정

Render에서 배포할 때:
- **Start Command**: `python auto_sender_daemon.py wint365`
- **Build Command**: `pip install -r requirements.txt`
- **Plan**: Starter ($7/월) 권장

## 📌 중요사항

- PC 종료 후에도 계속 실행됩니다
- Firebase의 `auto_send_status.is_running`으로만 ON/OFF 제어
- 무료 플랜은 sleep되므로 Starter 플랜 권장

