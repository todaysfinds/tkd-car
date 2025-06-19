# 태권도 차량 관리 시스템

태권도장 학생들의 차량 운행 및 출석 관리를 위한 웹 애플리케이션입니다.

## 주요 기능

- **오늘의 일정**: 당일 픽업/드롭오프 스케줄 관리
- **학생 관리**: 학생 정보 및 차량 이용 정보 관리
- **일정 관리**: 요일별, 시간대별 차량 운행 스케줄 관리
- **장소 관리**: 픽업 장소별 학생 그룹 관리
- **결석/변경 요청**: 학부모 결석 신청 및 관리자 승인

## 기술 스택

- **Backend**: Flask, SQLAlchemy
- **Database**: PostgreSQL (Production), SQLite (Development)
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render

## 배포

### Render 환경변수 설정

Render 대시보드에서 다음 환경변수를 설정해주세요:

1. `DATABASE_URL`: PostgreSQL 데이터베이스 URL (Render에서 자동 생성)
2. `SECRET_KEY`: Flask 시크릿 키 (랜덤한 문자열)

### 로컬 개발

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python app.py
```

## 프로젝트 구조

```
08-tkd-car/
├── app.py              # Flask 애플리케이션 메인 파일
├── requirements.txt    # Python 의존성
├── runtime.txt        # Python 버전 지정
├── Procfile           # Render 배포 설정
├── templates/         # HTML 템플릿
└── static/           # CSS, JS 정적 파일
``` 