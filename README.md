# 태권도 차량 관리 시스템

안정적이고 깔끔한 PostgreSQL 기반 차량 관리 시스템입니다.

## 🚀 **로컬 개발 환경 설정**

### 1️⃣ **PostgreSQL 설치 및 설정**

#### Windows (PostgreSQL 공식 설치)
```bash
# 1. PostgreSQL 공식 사이트에서 다운로드 및 설치
# https://www.postgresql.org/download/windows/

# 2. 데이터베이스 생성
psql -U postgres
CREATE DATABASE tkd_transport;
\q
```

#### macOS (Homebrew)
```bash
# PostgreSQL 설치
brew install postgresql@15
brew services start postgresql@15

# 데이터베이스 생성
createdb tkd_transport
```

#### Docker 사용 (모든 OS)
```bash
# PostgreSQL 컨테이너 실행
docker run --name tkd-postgres \
  -e POSTGRES_DB=tkd_transport \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15

# 연결 테스트
docker exec -it tkd-postgres psql -U postgres -d tkd_transport
```

### 2️⃣ **Python 환경 설정**

```bash
# 가상환경 생성 및 활성화
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3️⃣ **환경 변수 설정**

`.env` 파일 생성:
```env
# 로컬 개발용 (선택사항 - 기본값 사용 가능)
# DATABASE_URL=postgresql://postgres:password@localhost:5432/tkd_transport
SECRET_KEY=your-local-secret-key
```

### 4️⃣ **애플리케이션 실행**

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 🌐 **Render 배포 설정**

### 1️⃣ **Render PostgreSQL 데이터베이스 생성**

1. [Render 대시보드](https://dashboard.render.com)에서 "New +" → "PostgreSQL" 선택
2. 데이터베이스 이름: `tkd-transport-db`
3. 생성 후 "Internal Database URL" 복사

### 2️⃣ **Web Service 배포**

1. "New +" → "Web Service" 선택
2. GitHub 저장소 연결
3. 환경 변수 설정:
   ```
   DATABASE_URL=<PostgreSQL Internal Database URL>
   SECRET_KEY=<강력한 비밀키 생성>
   ```

### 3️⃣ **자동 배포 설정**

- GitHub에 push하면 자동으로 배포됩니다
- 데이터베이스는 영구적으로 보존됩니다

## 🎯 **주요 특징**

### ✅ **안정성**
- **PostgreSQL**: 프로덕션급 데이터베이스
- **데이터 보존**: 배포시 데이터 손실 없음
- **트랜잭션 안전성**: ACID 완전 지원

### ✅ **단순성**
- **환경 통합**: 개발/프로덕션 동일한 로직
- **자동 초기화**: 빈 DB시 자동으로 샘플 데이터 추가
- **Zero Config**: 복잡한 설정 없음

### ✅ **확장성**
- **동시 접속**: 여러 사용자 동시 사용 가능
- **대용량 데이터**: 수천 명 학생 데이터 처리
- **백업/복구**: Render 자동 백업

## 📁 **프로젝트 구조**

```
08-tkd-car/
├── app.py              # 메인 애플리케이션
├── requirements.txt    # Python 의존성
├── Procfile           # Render 배포 설정
├── runtime.txt        # Python 버전
├── templates/         # HTML 템플릿
├── static/           # CSS, JS 파일
└── README.md         # 이 파일
```

## 🔧 **데이터베이스 스키마**

- **Student**: 학생 정보
- **Schedule**: 시간표 정보  
- **Request**: 결석 신청
- **Attendance**: 출석 기록
- **QuickCallNumber**: 빠른 전화번호
- **Location**: 장소 정보

## 🆘 **문제 해결**

### 로컬 PostgreSQL 연결 실패
```bash
# 서비스 상태 확인
# Windows: 서비스 관리자에서 PostgreSQL 확인
# macOS: brew services list | grep postgresql
# Docker: docker ps

# 포트 확인
netstat -an | grep 5432
```

### Render 배포 실패
1. 로그 확인: Render 대시보드 → 서비스 → "Logs" 탭
2. 환경 변수 확인: DATABASE_URL, SECRET_KEY 설정 여부
3. PostgreSQL 데이터베이스 상태 확인

## 📞 **지원**

문제가 있으시면 GitHub Issues에 등록해주세요.

---

**🎉 이제 안정적이고 확장 가능한 시스템을 사용하실 수 있습니다!** 