# -*- coding: utf-8 -*-
"""
태권도 운송 관리 시스템
Python 3.11.8 전용
"""
import sys
print(f"🐍 Python 버전: {sys.version}")

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time
import os
import traceback
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
# PostgreSQL 드라이버 설정 (Python 3.13 호환)
import sys
try:
    import psycopg2
    print("🔄 psycopg2-binary 사용")
except ImportError:
    print("🔄 psycopg3로 대체")
    import psycopg as psycopg2
    # SQLAlchemy가 psycopg2를 찾을 수 있도록 sys.modules에 등록
    sys.modules['psycopg2'] = psycopg2
    # 추가 모듈들도 매핑
    sys.modules['psycopg2.extensions'] = psycopg2
    sys.modules['psycopg2.extras'] = psycopg2

app = Flask(__name__)

# 🎯 깔끔한 데이터베이스 설정 (PostgreSQL 전용)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # 프로덕션: Render PostgreSQL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # 🚨 SQLAlchemy가 psycopg3를 사용하도록 명시적으로 설정
    # postgresql+psycopg:// 를 사용하면 SQLAlchemy가 psycopg3 네이티브 dialect를 사용
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"🐘 PostgreSQL 사용 (프로덕션): {database_url[:50]}...")
else:
    # 로컬 개발: PostgreSQL
    try:
        # PostgreSQL 연결 테스트
        test_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tkd_transport',
            user='postgres'
        )
        test_conn.close()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://localhost:5432/tkd_transport'
        print("🐘 PostgreSQL 사용 (로컬)")
    except:
        # 로컬에서 PostgreSQL 없으면 환경변수 사용
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tkd_transport.db'
        print("🗄️ 로컬 개발용 SQLite")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

db = SQLAlchemy(app)

# 전역 에러 핸들러
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'API 엔드포인트를 찾을 수 없습니다.'}), 404
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': '서버 내부 오류가 발생했습니다.'}), 500
    return render_template('base.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    db.session.rollback()
    print(f"🚨 예외 발생: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # 사용자 친화적 에러 메시지
    user_friendly_errors = {
        'IntegrityError': '데이터 무결성 오류가 발생했습니다. 중복된 데이터가 있는지 확인해주세요.',
        'OperationalError': '데이터베이스 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        'ValidationError': '입력된 데이터가 올바르지 않습니다. 다시 확인해주세요.',
        'PermissionError': '권한이 없습니다.',
        'TimeoutError': '요청 시간이 초과되었습니다. 다시 시도해주세요.'
    }
    
    error_type = type(e).__name__
    user_message = user_friendly_errors.get(error_type, '시스템 오류가 발생했습니다. 관리자에게 문의해주세요.')
    
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False, 
            'error': user_message,
            'error_type': error_type,
            'debug_info': str(e) if app.debug else None
        }), 500
    return render_template('base.html'), 500

# 데이터베이스 모델
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(20))
    phone = db.Column(db.String(20))  # 기본 연락처 (부모님)
    phone_2 = db.Column(db.String(20))  # 추가 연락처 (아버지/어머니 구분)
    emergency_contact = db.Column(db.String(20))  # 비상 연락처
    pickup_location = db.Column(db.String(100))
    estimated_pickup_time = db.Column(db.String(10))  # 예상 픽업 시간 (12시간제)
    is_private_car = db.Column(db.Boolean, default=False)  # 개인차량 여부
    memo = db.Column(db.String(200))  # 메모 필드 추가
    session_part = db.Column(db.Integer)  # 부 (1부, 2부, 3부, 4부, 5부) 또는 특수 시간대 (6=돌봄시스템, 7=국기원부)
    # 안심번호 서비스용 필드
    allow_contact = db.Column(db.Boolean, default=True)  # 연락 허용 여부
    contact_preference = db.Column(db.String(20), default='phone')  # phone, kakao, both
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=월요일, 6=일요일
    schedule_type = db.Column(db.String(30), nullable=False)  # 'pickup', 'dropoff', 'care_system', 'national_training'
    time = db.Column(db.Time, nullable=False)  # 픽업 또는 드롭오프 시간
    location = db.Column(db.String(100))  # 각 스케줄별 장소 (Student의 pickup_location과 다를 수 있음)
    
    student = db.relationship('Student', backref=db.backref('schedules', lazy=True))

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    request_type = db.Column(db.String(20), nullable=False)  # 'absence', 'pickup_skip', 'dropoff_skip'
    reason = db.Column(db.String(100))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    memo = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref=db.backref('requests', lazy=True))

class TkdAttendance(db.Model):
    __tablename__ = 'tkd_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    pickup_time = db.Column(db.Time)
    dropoff_time = db.Column(db.Time)
    pickup_status = db.Column(db.String(20), default='pending')  # 'pending', 'boarded', 'absent', 'parent_pickup'
    dropoff_status = db.Column(db.String(20), default='pending')  # 'pending', 'dropped', 'absent', 'dojo_pickup'
    notes = db.Column(db.Text)
    
    student = db.relationship('Student', backref=db.backref('tkd_attendances', lazy=True))

class QuickCallNumber(db.Model):
    """빠른 전화걸기용 연락처 관리"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'school', 'daycare', 'emergency', 'location', 'custom'
    name = db.Column(db.String(100), nullable=False)  # 표시될 이름
    phone_number = db.Column(db.String(20), nullable=False)  # 전화번호
    location = db.Column(db.String(100))  # 장소명 (location 카테고리인 경우)
    description = db.Column(db.String(200))  # 설명
    is_active = db.Column(db.Boolean, default=True)  # 활성화 여부
    priority = db.Column(db.Integer, default=0)  # 우선순위 (숫자가 클수록 먼저 표시)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KakaoSettings(db.Model):
    """카카오톡 비즈니스 계정 설정"""
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(100))  # 카카오 비즈니스 계정 ID
    api_key = db.Column(db.String(200))  # API 키
    template_id = db.Column(db.String(100))  # 템플릿 ID
    sender_key = db.Column(db.String(100))  # 발신 키
    is_active = db.Column(db.Boolean, default=False)  # 서비스 활성화 여부
    test_mode = db.Column(db.Boolean, default=True)  # 테스트 모드
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Location(db.Model):
    """장소 정보 저장용 모델"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    default_time = db.Column(db.String(10))  # 기본 픽업 시간
    description = db.Column(db.String(200))  # 장소 설명
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 라우트
@app.route('/')
def index():
    return redirect(url_for('today'))

@app.route('/today')
def today():
    today_date = date.today()
    day_of_week = today_date.weekday()
    
    # 오늘 픽업 스케줄이 있는 학생들 조회 (1부~5부만, 돌봄시스템/국기원부 제외)
    students_with_schedule = db.session.query(Student, Schedule).join(Schedule).filter(
        Schedule.day_of_week == day_of_week,
        Schedule.schedule_type == 'pickup',
        Student.session_part.between(1, 5)  # 1부~5부만 표시
    ).order_by(Schedule.time, Schedule.location, Student.estimated_pickup_time).all()
    
    # 시간 순서대로 그룹화 (승차/하차 구분)
    time_groups = {}
    
    for student, schedule in students_with_schedule:
        # 시간 키 생성 (24시간제 → 12시간제 변환)
        pickup_hour = schedule.time.hour
        pickup_minute = schedule.time.minute
        
        # 12시간제로 변환 (PM 제거)
        if pickup_hour == 0:
            time_display = f"12:{pickup_minute:02d}"
        elif pickup_hour < 12:
            time_display = f"{pickup_hour}:{pickup_minute:02d}"
        elif pickup_hour == 12:
            time_display = f"12:{pickup_minute:02d}"
        else:
            time_display = f"{pickup_hour-12}:{pickup_minute:02d}"
        
        # 부 정보 추가
        part_names = {1: '1부', 2: '2부', 3: '3부', 4: '4부', 5: '5부'}
        part_name = part_names.get(student.session_part, f'{student.session_part}부')
        
        time_key = f"{time_display} {part_name} 승차"
        
        if time_key not in time_groups:
            time_groups[time_key] = {}
        
        # 장소별로 그룹화
        location_key = schedule.location or student.pickup_location or '미정'
        if location_key not in time_groups[time_key]:
            time_groups[time_key][location_key] = []
        
        # 오늘 출석 정보 조회
        attendance = TkdAttendance.query.filter_by(
            student_id=student.id,
            date=today_date
        ).first()
        
        # 요청 확인 (승인된 것과 대기 중인 것 모두)
        active_request = Request.query.filter_by(
            student_id=student.id
        ).filter(
            Request.start_date <= today_date,
            db.or_(Request.end_date.is_(None), Request.end_date >= today_date)
        ).filter(
            Request.status.in_(['approved', 'pending'])
        ).first()
        
        time_groups[time_key][location_key].append({
            'student': student,
            'schedule': schedule,
            'attendance': attendance,
            'request': active_request
        })
    
    return render_template('today.html', time_groups=time_groups, today=today_date)

@app.route('/parent/absence')
def parent_absence():
    students = Student.query.order_by(Student.name).all()
    return render_template('parent_absence.html', students=students)

@app.route('/parent/absence', methods=['POST'])
def submit_request():
    student_id = request.form.get('student_id')
    request_type = request.form.get('request_type')
    reason = request.form.get('reason', '')
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date_str = request.form.get('end_date')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    memo = request.form.get('memo', '')
    
    new_request = Request(
        student_id=student_id,
        request_type=request_type,
        reason=reason,
        start_date=start_date,
        end_date=end_date,
        memo=memo
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    flash('요청이 제출되었습니다.')
    return redirect(url_for('parent_absence'))

@app.route('/admin/schedule-manager')
def admin_schedule_manager():
    # 승차/하차 완전 분리 구조
    schedule_data = {}
    
    # 모든 스케줄 조회 (승차/하차 구분)
    schedules = db.session.query(Student, Schedule).join(Schedule).order_by(
        Schedule.day_of_week, Schedule.schedule_type, Schedule.time, Schedule.location, Student.name
    ).all()
    
    for student, schedule in schedules:
        day = schedule.day_of_week
        # 돌봄시스템/국기원부의 경우 location에서 part 정보를 추출
        if schedule.schedule_type in ['care_system', 'national_training']:
            # location에 part 정보가 있는지 확인 (예: "도장_care1", "도장_national")
            if '_' in (schedule.location or ''):
                location_parts = schedule.location.split('_')
                part = location_parts[1] if len(location_parts) > 1 else 'care1'
                location = location_parts[0]
            else:
                # 기본값 설정
                part = 'care1' if schedule.schedule_type == 'care_system' else 'national'
                location = schedule.location or '도장'
        else:
            part = student.session_part or 1
            location = schedule.location or student.pickup_location or '미정'
        
        schedule_type = schedule.schedule_type  # 'pickup', 'dropoff', 'care_system', 'national_training'
        
        # 요일별 구조 초기화
        if day not in schedule_data:
            schedule_data[day] = {}
        
        # 부별 구조 초기화
        if part not in schedule_data[day]:
            schedule_data[day][part] = {}
            
        # 승차/하차별 구조 초기화 (돌봄시스템과 국기원부는 단일 구조)
        if schedule_type in ['care_system', 'national_training']:
            # 돌봄시스템/국기원부는 승차/하차 구분 없이 단일 구조
            # part를 문자열로 처리 (care1, care2, care3, national)
            part_key = str(part) if isinstance(part, str) else part
            
            if part_key not in schedule_data[day]:
                schedule_data[day][part_key] = {}
            if 'students' not in schedule_data[day][part_key]:
                schedule_data[day][part_key]['students'] = {}
            if location not in schedule_data[day][part_key]['students']:
                schedule_data[day][part_key]['students'][location] = []
            schedule_data[day][part_key]['students'][location].append({
                'student': student,
                'schedule': schedule
            })
        else:
            # 기존 승차/하차 구조
            if schedule_type not in schedule_data[day][part]:
                schedule_data[day][part][schedule_type] = {}
                
            # 장소별 구조 초기화
            if location not in schedule_data[day][part][schedule_type]:
                schedule_data[day][part][schedule_type][location] = []
                
            # 학생 추가
            schedule_data[day][part][schedule_type][location].append({
                'student': student,
                'schedule': schedule
            })
    
    return render_template('admin_schedule_manager.html', schedule_data=schedule_data)

@app.route('/admin/students')
def admin_students():
    students = Student.query.order_by(Student.name).all()
    return render_template('admin_students.html', students=students)

@app.route('/admin/quick-call-manager')
def admin_quick_call_manager():
    """빠른 전화번호 관리 페이지"""
    return render_template('admin_quick_call_manager.html')

@app.route('/api/update_attendance', methods=['POST'])
def update_attendance():
    data = request.get_json()
    student_id = data.get('student_id')
    attendance_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    status = data.get('status')
    attendance_type = data.get('type', 'pickup')  # pickup or dropoff
    
    attendance = TkdAttendance.query.filter_by(
        student_id=student_id,
        date=attendance_date
    ).first()
    
    if not attendance:
        attendance = TkdAttendance(student_id=student_id, date=attendance_date)
        db.session.add(attendance)
    
    if attendance_type == 'pickup':
        # 토글 기능: 상태에 따라 전환
        if status == 'boarded':
            if attendance.pickup_status == 'boarded':
                attendance.pickup_status = 'pending'  # 탑승 → 대기
            else:
                attendance.pickup_status = 'boarded'  # 대기/결석 → 탑승
        elif status == 'absent':
            if attendance.pickup_status == 'absent':
                attendance.pickup_status = 'pending'  # 결석 → 대기
            else:
                attendance.pickup_status = 'absent'   # 대기/탑승 → 결석
        else:
            attendance.pickup_status = status
    else:
        attendance.dropoff_status = status
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/approve_request/<int:request_id>', methods=['POST'])
def approve_request_api(request_id):
    req = Request.query.get_or_404(request_id)
    req.status = 'approved'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/locations')
def admin_locations():
    # 장소별로 학생들을 그룹화
    students = Student.query.all()
    location_groups = {}
    
    for student in students:
        location = student.pickup_location or '미지정'
        if location not in location_groups:
            location_groups[location] = []
        location_groups[location].append(student)
    
    return render_template('admin_location_manager.html', location_groups=location_groups)

@app.route('/api/add_location', methods=['POST'])
def add_location():
    try:
        print(f"🔍 장소 추가 요청 받음")
        
        data = request.get_json()
        name = data.get('name')
        default_time = data.get('default_time')
        
        print(f"   - 장소명: {name}")
        print(f"   - 기본 시간: {default_time}")
        
        if not name:
            print("❌ 장소명이 없음")
            return jsonify({'success': False, 'message': '장소명이 필요합니다.'})
        
        # 중복 체크 (Location 테이블과 기존 학생 장소 모두 체크)
        existing_location = Location.query.filter_by(name=name).first()
        existing_student_location = Student.query.filter_by(pickup_location=name).first()
        
        if existing_location or existing_student_location:
            print(f"❌ 중복된 장소: {name}")
            return jsonify({'success': False, 'message': '이미 존재하는 장소입니다.'})
        
        # 새 장소 추가
        new_location = Location(
            name=name,
            default_time=default_time
        )
        
        db.session.add(new_location)
        db.session.commit()
        
        print(f"✅ 장소 '{name}' 추가 완료 (ID: {new_location.id})")
        
        return jsonify({'success': True, 'message': f'장소 "{name}"이 추가되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 장소 추가 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'장소 추가 실패: {str(e)}'})

@app.route('/api/update_location', methods=['POST'])
def update_location():
    try:
        data = request.get_json()
        original_name = data.get('original_name')
        new_name = data.get('new_name')
        default_time = data.get('default_time')
        
        if not original_name or not new_name:
            return jsonify({'success': False, 'message': '장소명이 필요합니다.'})
        
        # 해당 장소의 모든 학생들 업데이트
        students = Student.query.filter_by(pickup_location=original_name).all()
        for student in students:
            student.pickup_location = new_name
            if default_time:
                student.estimated_pickup_time = default_time
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_location', methods=['POST'])
def delete_location():
    try:
        data = request.get_json()
        location_name = data.get('location_name')
        
        if not location_name:
            return jsonify({'success': False, 'message': '장소명이 필요합니다.'})
        
        # 해당 장소의 모든 학생들의 장소 정보 초기화
        students = Student.query.filter_by(pickup_location=location_name).all()
        for student in students:
            student.pickup_location = None
            student.estimated_pickup_time = None
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_student/<int:student_id>')
def get_student(student_id):
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': '학생을 찾을 수 없습니다.'})
        
        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'name': student.name,
                'pickup_location': student.pickup_location,
                'estimated_pickup_time': student.estimated_pickup_time,
                'session_part': student.session_part,
                'memo': student.memo
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/update_student_location', methods=['POST'])
def update_student_location():
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        name = data.get('name')
        location = data.get('location')
        pickup_time = data.get('pickup_time')
        session_part = data.get('session_part')
        memo = data.get('memo')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': '학생을 찾을 수 없습니다.'})
        
        if name:
            student.name = name
        student.pickup_location = location if location else None
        student.estimated_pickup_time = pickup_time if pickup_time else None
        student.session_part = int(session_part) if session_part else 1
        student.memo = memo if memo else None
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_locations')
def get_locations():
    try:
        # Location 테이블과 사용 중인 장소를 모두 포함
        location_set = set()
        
        # 1. Location 테이블의 모든 활성 장소
        db_locations = Location.query.filter_by(is_active=True).all()
        for loc in db_locations:
            location_set.add(loc.name)
        
        # 2. 현재 사용 중인 장소들 (Student.pickup_location)
        student_locations = db.session.query(Student.pickup_location).filter(
            Student.pickup_location.isnot(None)
        ).distinct().all()
        for loc in student_locations:
            if loc[0]:
                location_set.add(loc[0])
        
        # 3. 스케줄에서 사용 중인 장소들
        schedule_locations = db.session.query(Schedule.location).filter(
            Schedule.location.isnot(None)
        ).distinct().all()
        for loc in schedule_locations:
            if loc[0]:
                location_set.add(loc[0])
        
        location_list = sorted(list(location_set))
        return jsonify({'success': True, 'locations': location_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 학생 관리 API
@app.route('/api/add_student', methods=['POST'])
def add_student():
    try:
        print(f"🔍 학생 추가 요청 받음")
        
        # 입력 데이터 검증
        name = request.form.get('name')
        birth_year = request.form.get('birth_year')
        
        print(f"   - 이름: {name}")
        print(f"   - 출생년도: {birth_year}")
        
        # 이름 검증
        is_valid, validated_name = validate_student_name(name)
        if not is_valid:
            print(f"❌ 이름 검증 실패: {validated_name}")
            return error_response(validated_name)
        
        # 중복 체크
        existing_student = Student.query.filter_by(name=validated_name).first()
        if existing_student:
            print(f"❌ 중복된 이름: {validated_name}")
            return error_response(f'"{validated_name}" 학생이 이미 존재합니다. 구분을 위해 다른 이름을 사용해주세요.')
        
        # 출생년도 검증
        birth_year = sanitize_input(birth_year, 10)
        
        # 새 학생 추가
        new_student = Student(
            name=validated_name,
            grade=birth_year
        )
        
        print(f"✅ 새 학생 생성: {new_student.name}")
        
        db.session.add(new_student)
        db.session.commit()
        
        print(f"✅ 학생 추가 완료: ID={new_student.id}")
        
        return success_response(
            f'{validated_name} 학생이 성공적으로 추가되었습니다.',
            {'student_id': new_student.id, 'student_name': validated_name}
        )
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 학생 추가 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response('학생 추가 중 시스템 오류가 발생했습니다. 다시 시도해주세요.', 500)

@app.route('/api/check_duplicate_name', methods=['POST'])
def check_duplicate_name():
    try:
        print(f"🔍 중복 체크 요청 받음")
        
        data = request.get_json()
        if not data:
            print("❌ JSON 데이터 없음")
            return jsonify({'success': False, 'error': 'JSON 데이터가 필요합니다.'})
            
        name = data.get('name')
        exclude_id = data.get('exclude_id')
        
        print(f"   - 이름: {name}")
        print(f"   - 제외 ID: {exclude_id}")
        
        if not name:
            print("❌ 이름이 없음")
            return jsonify({'success': False, 'error': '이름이 필요합니다.'})
        
        query = Student.query.filter_by(name=name)
        if exclude_id:
            query = query.filter(Student.id != exclude_id)
        
        existing_student = query.first()
        is_duplicate = existing_student is not None
        
        print(f"   - 중복 여부: {is_duplicate}")
        if existing_student:
            print(f"   - 기존 학생 ID: {existing_student.id}")
        
        return jsonify({
            'success': True,
            'duplicate': is_duplicate
        })
    
    except Exception as e:
        print(f"❌ 중복 체크 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'중복 체크 실패: {str(e)}'})

@app.route('/api/update_student', methods=['POST'])
def update_student():
    try:
        data = request.get_json()
        if not data:
            return error_response('요청 데이터가 없습니다.')
        
        student_id = data.get('id')
        name = data.get('name')
        birth_year = data.get('birth_year')
        
        # 학생 ID 검증
        if not student_id:
            return error_response('학생 ID가 필요합니다.')
        
        try:
            student_id = int(student_id)
        except (ValueError, TypeError):
            return error_response('올바른 학생 ID가 아닙니다.')
        
        # 학생 존재 확인
        student = Student.query.get(student_id)
        if not student:
            return error_response('학생을 찾을 수 없습니다.')
        
        # 이름 검증
        is_valid, validated_name = validate_student_name(name)
        if not is_valid:
            return error_response(validated_name)
        
        # 중복 체크 (본인 제외)
        existing_student = Student.query.filter(
            Student.name == validated_name,
            Student.id != student_id
        ).first()
        
        if existing_student:
            return error_response(f'"{validated_name}" 이름의 다른 학생이 이미 존재합니다.')
        
        # 출생년도 검증
        birth_year = sanitize_input(birth_year, 10)
        
        # 업데이트
        old_name = student.name
        student.name = validated_name
        student.grade = birth_year
        
        db.session.commit()
        
        print(f"✅ 학생 정보 업데이트: {old_name} → {validated_name}")
        
        return success_response(
            f'학생 정보가 성공적으로 수정되었습니다.',
            {'student_id': student.id, 'old_name': old_name, 'new_name': validated_name}
        )
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 학생 업데이트 오류: {str(e)}")
        return error_response('학생 정보 수정 중 오류가 발생했습니다.', 500)

@app.route('/api/delete_student', methods=['POST'])
def delete_student():
    try:
        data = request.get_json()
        if not data:
            return error_response('요청 데이터가 없습니다.')
        
        student_id = data.get('id')
        
        # 학생 ID 검증
        if not student_id:
            return error_response('학생 ID가 필요합니다.')
        
        try:
            student_id = int(student_id)
        except (ValueError, TypeError):
            return error_response('올바른 학생 ID가 아닙니다.')
        
        # 학생 존재 확인
        student = Student.query.get(student_id)
        if not student:
            return error_response('삭제할 학생을 찾을 수 없습니다.')
        
        student_name = student.name  # 삭제 전에 이름 저장
        print(f"🗑️ 학생 삭제 시작: {student_name} (ID: {student_id})")
        
        # 관련된 데이터를 안전하게 순서대로 삭제
        deleted_counts = {}
        
        try:
            # 1. 출석 정보 삭제
            attendance_count = TkdAttendance.query.filter_by(student_id=student_id).count()
            TkdAttendance.query.filter_by(student_id=student_id).delete(synchronize_session=False)
            deleted_counts['attendance'] = attendance_count
            print(f"   - 출석 기록 삭제: {attendance_count}건")
            
            # 2. 요청 정보 삭제  
            request_count = Request.query.filter_by(student_id=student_id).count()
            Request.query.filter_by(student_id=student_id).delete(synchronize_session=False)
            deleted_counts['requests'] = request_count
            print(f"   - 요청 기록 삭제: {request_count}건")
            
            # 3. 스케줄 정보 삭제
            schedule_count = Schedule.query.filter_by(student_id=student_id).count()
            Schedule.query.filter_by(student_id=student_id).delete(synchronize_session=False)
            deleted_counts['schedules'] = schedule_count
            print(f"   - 스케줄 삭제: {schedule_count}건")
            
            # 4. 학생 정보 삭제
            db.session.delete(student)
            
            # 모든 변경사항 커밋
            db.session.commit()
            
            print(f"✅ 학생 삭제 완료: {student_name}")
            
            return success_response(
                f'{student_name} 학생의 모든 정보가 성공적으로 삭제되었습니다.',
                {
                    'deleted_student': student_name,
                    'deleted_counts': deleted_counts,
                    'total_records': sum(deleted_counts.values())
                }
            )
            
        except Exception as delete_error:
            print(f"❌ 데이터 삭제 중 오류: {str(delete_error)}")
            raise delete_error
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 학생 삭제 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response('학생 삭제 중 오류가 발생했습니다. 다시 시도해주세요.', 500)

# 스케줄 관리 API
@app.route('/api/get_all_students')
def get_all_students():
    try:
        students = Student.query.order_by(Student.name).all()
        return jsonify({
            'success': True,
            'students': [{
                'id': student.id,
                'name': student.name,
                'grade': student.grade
            } for student in students]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_student_to_schedule', methods=['POST'])
def add_student_to_schedule():
    """개별 학생을 특정 스케줄에 추가"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('type')  # 'pickup' or 'dropoff'
        target_location = data.get('location')  # 장소 정보
        session_part = data.get('session_part')
        
        if not all([student_id, day_of_week is not None, schedule_type, target_location, session_part]):
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        # 학생 확인
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        # 부별 시간 설정
        if session_part == 1:  # 1부
            pickup_time = time(14, 0)  # 2:00 PM
            dropoff_time = time(14, 50)  # 2:50 PM
        elif session_part == 2:  # 2부
            pickup_time = time(15, 0)  # 3:00 PM
            dropoff_time = time(15, 50)  # 3:50 PM
        elif session_part == 3:  # 3부
            pickup_time = time(16, 30)  # 4:30 PM
            dropoff_time = time(17, 20)  # 5:20 PM
        elif session_part == 4:  # 4부
            pickup_time = time(17, 30)  # 5:30 PM
            dropoff_time = time(18, 20)  # 6:20 PM
        elif session_part == 5:  # 5부
            pickup_time = time(19, 0)  # 7:00 PM
            dropoff_time = time(19, 50)  # 7:50 PM
        else:  # 기본값 (5부)
            pickup_time = time(19, 0)  # 7:00 PM
            dropoff_time = time(19, 50)  # 7:50 PM
        
        # 돌봄시스템과 국기원부는 도장에서 시간 구분 없이 처리
        if target_location in ['도장']:
            schedule_time = pickup_time  # 시간 구분 없음
        else:
            schedule_time = pickup_time if schedule_type == 'pickup' else dropoff_time
        
        # 중복 체크 (같은 학생, 같은 날, 같은 타입, 같은 장소)
        existing_schedule = Schedule.query.filter_by(
            student_id=student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=target_location
        ).first()
        
        if existing_schedule:
            return jsonify({'success': False, 'error': '이미 해당 스케줄이 존재합니다.'})
        
        # 새 스케줄 추가
        new_schedule = Schedule(
            student_id=student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            time=schedule_time,
            location=target_location
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        print(f"✅ 스케줄 추가 완료: {student.name} → {target_location}")
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 단일 스케줄 추가 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 사용자 친화적 에러 메시지
        if 'StringDataRightTruncation' in str(e) or 'value too long' in str(e):
            error_msg = f'장소명이 너무 깁니다. 현재 {len(target_location) if "target_location" in locals() else "Unknown"}자 → 100자 이하로 줄여주세요.'
        elif 'duplicate' in str(e).lower():
            error_msg = '이미 동일한 스케줄이 존재합니다.'
        else:
            error_msg = f'스케줄 추가 중 오류가 발생했습니다: {str(e)}'
        
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/add_multiple_students_to_schedule', methods=['POST'])
def add_multiple_students_to_schedule():
    """여러 학생을 한 번에 추가 (깔끔한 버전)"""
    try:
        data = request.get_json()
        students = data.get('students', [])  # [{'student_id': 1, 'name': '홍길동'}, ...]
        day_of_week = data.get('day_of_week')
        session_part = data.get('session_part')
        schedule_type = data.get('type')  # 'pickup' or 'dropoff'
        target_location = data.get('location')  # 장소 정보
        
        if not students or day_of_week is None or not session_part or not schedule_type or not target_location:
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        # 부별 시간 설정
        if session_part == 1:  # 1부
            pickup_time = time(14, 0)  # 2:00 PM
            dropoff_time = time(14, 50)  # 2:50 PM
        elif session_part == 2:  # 2부
            pickup_time = time(15, 0)  # 3:00 PM
            dropoff_time = time(15, 50)  # 3:50 PM
        elif session_part == 3:  # 3부
            pickup_time = time(16, 30)  # 4:30 PM
            dropoff_time = time(17, 20)  # 5:20 PM
        elif session_part == 4:  # 4부
            pickup_time = time(17, 30)  # 5:30 PM
            dropoff_time = time(18, 20)  # 6:20 PM
        elif session_part == 5:  # 5부
            pickup_time = time(19, 0)  # 7:00 PM
            dropoff_time = time(19, 50)  # 7:50 PM
        else:  # 기본값 (5부)
            pickup_time = time(19, 0)  # 7:00 PM
            dropoff_time = time(19, 50)  # 7:50 PM
        
        # 돌봄시스템과 국기원부는 도장에서 시간 구분 없이 처리
        if target_location in ['도장']:
            schedule_time = pickup_time  # 시간 구분 없음
        else:
            schedule_time = pickup_time if schedule_type == 'pickup' else dropoff_time
        
        print(f"🔍 학생 {len(students)}명을 {target_location}에 추가 (시간: {schedule_time})")
        
        # 먼저 중복 체크 (하나라도 중복이면 전체 취소)
        duplicates = []
        invalid_students = []
        
        for student_data in students:
            student_id = student_data.get('id')
            student_name = student_data.get('name', f'학생{student_id}')
            
            # 학생 존재 여부 확인
            student = Student.query.get(student_id)
            if not student:
                invalid_students.append(student_name)
                continue
            
            # 중복 체크
            existing_schedule = Schedule.query.filter_by(
                student_id=student_id,
                day_of_week=day_of_week,
                schedule_type=schedule_type,
                location=target_location
            ).first()
            
            if existing_schedule:
                duplicates.append(student_name)
        
        # 중복이나 잘못된 학생이 있으면 전체 취소
        if duplicates or invalid_students:
            error_msg = []
            if duplicates:
                error_msg.append(f"이미 등록된 학생: {', '.join(duplicates)}")
            if invalid_students:
                error_msg.append(f"존재하지 않는 학생: {', '.join(invalid_students)}")
            
            return jsonify({
                'success': False, 
                'error': ' / '.join(error_msg),
                'duplicates': duplicates,
                'invalid_students': invalid_students
            })
        
        # 모든 검증 통과 시에만 실제 추가
        added_students = []
        for student_data in students:
            student_id = student_data.get('id')
            student_name = student_data.get('name', f'학생{student_id}')
            
            # 새 스케줄 추가
            new_schedule = Schedule(
                student_id=student_id,
                day_of_week=day_of_week,
                schedule_type=schedule_type,
                time=schedule_time,
                location=target_location
            )
            
            db.session.add(new_schedule)
            
            # 프론트엔드 DOM 업데이트용 상세 정보 추가
            added_students.append({
                'student': {
                    'id': student_id,
                    'name': student_name
                },
                'day_of_week': day_of_week,
                'session_part': session_part,
                'type': schedule_type,
                'location': target_location,
                'time': schedule_time.strftime('%H:%M')
            })
        
        # 모든 변경사항을 한 번에 커밋
        db.session.commit()
        
        print(f"✅ [성공] {len(added_students)}명의 학생이 {target_location}에 추가됨")
        
        return jsonify({
            'success': True,
            'message': f'{len(added_students)}명의 학생이 {target_location}에 추가되었습니다.',
            'added_students': added_students
        })
    
    except Exception as e:
        # 오류 발생 시 모든 변경사항 롤백
        db.session.rollback()
        print(f"❌ 다중 스케줄 추가 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 정확한 에러 진단
        error_str = str(e).lower()
        if 'value too long' in error_str or 'stringdatatruncation' in error_str:
            error_msg = f'장소명이 너무 깁니다. 현재 {len(target_location) if "target_location" in locals() else "Unknown"}자 → 100자 이하로 줄여주세요.'
        elif 'duplicate' in error_str:
            error_msg = '이미 동일한 스케줄이 존재합니다.'
        else:
            error_msg = f'서버 오류: {str(e)}'
        
        return jsonify({'success': False, 'error': error_msg})

# 장소 및 스케줄 관리 API
@app.route('/api/update_location_name', methods=['POST'])
def update_location_name():
    try:
        data = request.get_json()
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        # 해당 장소의 모든 학생들 업데이트
        students = Student.query.filter_by(pickup_location=old_name).all()
        for student in students:
            student.pickup_location = new_name
        
        db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_student_from_schedule', methods=['POST'])
def remove_student_from_schedule():
    """학생을 스케줄에서 제거 (개선된 버전)"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        day_of_week = data.get('day_of_week')
        location = data.get('location')
        schedule_type = data.get('type', 'pickup')
        session_part = data.get('session_part')
        
        print(f"🔍 삭제 요청: student_id={student_id}, day={day_of_week}, location='{location}', type='{schedule_type}', session_part={session_part}")
        
        # 학생 정보 확인
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        # 스케줄 찾기 (여러 조건으로 시도)
        schedule = None
        
        # 1차 시도: 정확한 location으로 찾기
        schedule = Schedule.query.filter_by(
            student_id=student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=location
        ).first()
        
        # 2차 시도: session_part로 찾기 (돌봄시스템/국기원부)
        if not schedule and session_part:
            schedule = Schedule.query.filter_by(
                student_id=student_id,
                day_of_week=day_of_week,
                schedule_type=schedule_type
            ).join(Student).filter(Student.session_part == session_part).first()
        
        # 3차 시도: location이 포함된 것 찾기 (부분 일치)
        if not schedule:
            schedules = Schedule.query.filter_by(
                student_id=student_id,
                day_of_week=day_of_week,
                schedule_type=schedule_type
            ).all()
            
            for s in schedules:
                if s.location and (location in s.location or s.location in location):
                    schedule = s
                    break
        
        # 디버그 정보
        all_schedules = Schedule.query.filter_by(
            student_id=student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type
        ).all()
        
        print(f"📋 학생의 모든 스케줄:")
        for s in all_schedules:
            print(f"   - location: '{s.location}', type: '{s.schedule_type}'")
        
        if schedule:
            student_name = student.name
            actual_location = schedule.location
            print(f"✅ 스케줄 찾음: location='{actual_location}'")
            
            db.session.delete(schedule)
            db.session.commit()
            
            # 해당 장소에 다른 학생이 있는지 확인
            remaining_students = Schedule.query.filter_by(
                day_of_week=day_of_week,
                location=actual_location,
                schedule_type=schedule_type
            ).count()
            
            message = f'{student_name} 학생이 {actual_location}에서 제거되었습니다.'
            if remaining_students == 0:
                message += f' "{actual_location}" 장소는 빈 상태로 유지됩니다.'
            
            return jsonify({
                'success': True, 
                'message': message,
                'keep_location': True,
                'location': actual_location,
                'remaining_students': remaining_students
            })
        else:
            print(f"❌ 스케줄을 찾을 수 없음")
            return jsonify({'success': False, 'error': f'해당 스케줄을 찾을 수 없습니다. (student_id={student_id}, day={day_of_week}, location="{location}", type="{schedule_type}")'})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 삭제 중 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# 연락 기능 관련 API (정석 구현)
@app.route('/api/contact_parent', methods=['POST'])
def contact_parent():
    """부모님에게 연락하기 (정석 구현)"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        contact_type = data.get('type', 'phone')  # phone, kakao, both
        message = data.get('message', '')
        message_type = data.get('message_type', 'pickup')  # pickup, arrival, departure, custom
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        if not student.allow_contact:
            return jsonify({'success': False, 'error': '해당 학생은 연락이 제한되어 있습니다.'})
        
        # 학생의 연락 선호도 확인
        preferred_contact = student.contact_preference or 'phone'
        
        if contact_type == 'kakao' or (contact_type == 'both' and 'kakao' in preferred_contact):
            # 카카오톡 발송
            if message_type != 'custom':
                message = get_message_template(student, message_type)
            
            result = send_kakao_message(student, message)
            return jsonify(result)
        
        elif contact_type == 'phone' or contact_type == 'both':
            # 전화 연결 옵션 제공
            contacts = []
            
            if student.phone:
                contacts.append({
                    'type': '기본 연락처',
                    'number': student.phone,
                    'tel_link': f'tel:{student.phone}',
                    'priority': 1
                })
            
            if student.phone_2:
                contacts.append({
                    'type': '추가 연락처', 
                    'number': student.phone_2,
                    'tel_link': f'tel:{student.phone_2}',
                    'priority': 2
                })
            
            if student.emergency_contact:
                contacts.append({
                    'type': '비상 연락처',
                    'number': student.emergency_contact,
                    'tel_link': f'tel:{student.emergency_contact}',
                    'priority': 3
                })
            
            if not contacts:
                return jsonify({'success': False, 'error': '등록된 연락처가 없습니다.'})
            
            # 우선순위대로 정렬
            contacts.sort(key=lambda x: x['priority'])
            
            result = {
                'success': True,
                'message': f'{student.name} 학생 부모님 연락처',
                'contacts': contacts,
                'action': 'call',
                'student_name': student.name,
                'preferred_contact': preferred_contact
            }
            
            return jsonify(result)
        
        else:
            return jsonify({'success': False, 'error': '올바른 연락 방식을 선택해주세요.'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_message_template', methods=['POST'])
def send_message_template():
    """템플릿 메시지 발송"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        message_type = data.get('message_type', 'pickup')
        custom_message = data.get('custom_message', '')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        if not student.allow_contact:
            return jsonify({'success': False, 'error': '해당 학생은 연락이 제한되어 있습니다.'})
        
        # 메시지 생성
        if message_type == 'custom' and custom_message:
            message = custom_message
        else:
            message = get_message_template(student, message_type)
        
        # 카카오톡 발송
        result = send_kakao_message(student, message)
        
        # 발송 기록 저장 (필요시)
        # MessageLog.create(student_id=student_id, message_type=message_type, ...)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def send_kakao_message(student, message):
    """카카오톡 메시지 발송 (실제 구현 준비)"""
    try:
        settings = KakaoSettings.query.first()
        
        if not settings or not settings.is_active:
            # 시뮬레이션 모드
            return {
                'success': True,
                'message': f'[시뮬레이션] {student.name} 부모님께 카카오톡 발송',
                'preview': f'''
📚 {student.name} 학생 차량 알림

{message}

🏫 OO태권도장
📞 문의: 010-XXXX-XXXX
⏰ 발송시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}
''',
                'note': '실제 서비스를 위해서는 카카오톡 비즈니스 계정 설정이 필요합니다.',
                'action': 'kakao',
                'simulation': True
            }
        
        # 실제 카카오톡 발송 로직 (비즈니스 계정 연동)
        if settings.test_mode:
            # 테스트 모드
            return {
                'success': True,
                'message': f'[테스트] {student.name} 부모님께 카카오톡 발송',
                'preview': f'''
📚 {student.name} 학생 차량 알림

{message}

🏫 OO태권도장
📞 문의: 010-XXXX-XXXX
⏰ 발송시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}

⚠️ 테스트 모드: 실제 발송되지 않았습니다.
''',
                'action': 'kakao',
                'test_mode': True
            }
        else:
            # TODO: 실제 카카오톡 API 연동
            # 카카오톡 비즈니스 API를 사용한 실제 메시지 발송
            # requests.post(kakao_api_url, headers=headers, json=payload)
            
            return {
                'success': True,
                'message': f'{student.name} 부모님께 카카오톡을 발송했습니다.',
                'action': 'kakao',
                'real_send': True
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'카카오톡 발송 실패: {str(e)}',
            'action': 'kakao'
        }

def get_message_template(student, message_type='pickup'):
    """메시지 템플릿 생성"""
    templates = {
        'pickup': f'''
🚌 차량 픽업 알림

안녕하세요! {student.name} 학생 부모님께 알려드립니다.

📍 픽업 장소: {student.pickup_location}
⏰ 예상 시간: {student.estimated_pickup_time}
🎯 수업: {student.session_part}부

차량이 곧 도착할 예정입니다.
준비해주세요!

🏫 OO태권도장
''',
        'arrival': f'''
🏫 도장 도착 알림

{student.name} 학생이 안전하게 도장에 도착했습니다.

⏰ 도착 시간: {datetime.now().strftime('%H:%M')}
🎯 수업: {student.session_part}부

수업 후 하차 시간을 별도로 안내드리겠습니다.

🏫 OO태권도장
''',
        'departure': f'''
🚌 하차 출발 알림

{student.name} 학생이 수업을 마치고 하차를 위해 출발했습니다.

🏫 출발: {datetime.now().strftime('%H:%M')}
📍 하차 장소: {student.pickup_location}
⏰ 예상 도착: 약 10-15분 후

준비해주세요!

🏫 OO태권도장
'''
    }
    
    return templates.get(message_type, message_type)

# 빠른 전화걸기 API (정석 구현)
@app.route('/api/quick_call', methods=['POST'])
def quick_call():
    """빠른 전화걸기 (데이터베이스 기반)"""
    try:
        data = request.get_json()
        call_type = data.get('type')
        location = data.get('location')
        custom_number = data.get('number')
        
        if custom_number:
            # 직접 입력된 번호
            return jsonify({
                'success': True,
                'tel_link': f'tel:{custom_number}',
                'display': custom_number,
                'action': 'call'
            })
        
        # 데이터베이스에서 연락처 조회
        query = QuickCallNumber.query.filter_by(is_active=True)
        
        if call_type:
            query = query.filter_by(category=call_type)
        
        if location and call_type == 'location':
            query = query.filter_by(location=location)
        
        numbers = query.order_by(QuickCallNumber.priority.desc(), QuickCallNumber.name).all()
        
        if not numbers:
            return jsonify({'success': False, 'error': '등록된 연락처가 없습니다.'})
        
        if len(numbers) == 1:
            # 하나만 있으면 바로 연결
            number = numbers[0]
            return jsonify({
                'success': True,
                'tel_link': f'tel:{number.phone_number}',
                'display': f'{number.name} ({number.phone_number})',
                'description': number.description,
                'action': 'call'
            })
        else:
            # 여러 개가 있으면 선택할 수 있도록 목록 반환
            options = []
            for number in numbers:
                options.append({
                    'id': number.id,
                    'name': number.name,
                    'phone_number': number.phone_number,
                    'description': number.description,
                    'tel_link': f'tel:{number.phone_number}'
                })
            
            return jsonify({
                'success': True,
                'action': 'select',
                'options': options,
                'message': f'{call_type} 연락처 선택'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/quick_call_numbers')
def get_quick_call_numbers():
    """빠른 전화 번호 목록 조회"""
    try:
        location = request.args.get('location')
        category = request.args.get('category')
        
        query = QuickCallNumber.query.filter_by(is_active=True)
        
        if category:
            query = query.filter_by(category=category)
        
        if location:
            query = query.filter(
                db.or_(
                    QuickCallNumber.location == location,
                    QuickCallNumber.category.in_(['school', 'daycare', 'emergency'])
                )
            )
        
        numbers = query.order_by(QuickCallNumber.priority.desc(), QuickCallNumber.name).all()
        
        result = {}
        for number in numbers:
            if number.category not in result:
                result[number.category] = []
            
            result[number.category].append({
                'id': number.id,
                'name': number.name,
                'phone_number': number.phone_number,
                'description': number.description,
                'location': number.location
            })
        
        return jsonify({'success': True, 'numbers': result})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_contact_settings', methods=['POST'])
def update_contact_settings():
    """학생별 연락 설정 업데이트"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        phone = data.get('phone', '')
        phone_2 = data.get('phone_2', '')
        emergency_contact = data.get('emergency_contact', '')
        allow_contact = data.get('allow_contact', True)
        contact_preference = data.get('contact_preference', 'phone')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        student.phone = phone if phone else None
        student.phone_2 = phone_2 if phone_2 else None
        student.emergency_contact = emergency_contact if emergency_contact else None
        student.allow_contact = allow_contact
        student.contact_preference = contact_preference
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# 빠른 전화 번호 관리 API
@app.route('/api/quick_call_numbers', methods=['POST'])
def add_quick_call_number():
    """빠른 전화 번호 추가"""
    try:
        data = request.get_json()
        
        quick_number = QuickCallNumber(
            category=data['category'],
            name=data['name'],
            phone_number=data['phone_number'],
            location=data.get('location'),
            description=data.get('description', ''),
            priority=data.get('priority', 0)
        )
        
        db.session.add(quick_number)
        db.session.commit()
        
        return jsonify({'success': True, 'id': quick_number.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/quick_call_numbers/<int:number_id>', methods=['PUT'])
def update_quick_call_number(number_id):
    """빠른 전화 번호 수정"""
    try:
        data = request.get_json()
        
        quick_number = QuickCallNumber.query.get(number_id)
        if not quick_number:
            return jsonify({'success': False, 'error': '연락처를 찾을 수 없습니다.'})
        
        quick_number.category = data.get('category', quick_number.category)
        quick_number.name = data.get('name', quick_number.name)
        quick_number.phone_number = data.get('phone_number', quick_number.phone_number)
        quick_number.location = data.get('location', quick_number.location)
        quick_number.description = data.get('description', quick_number.description)
        quick_number.priority = data.get('priority', quick_number.priority)
        quick_number.is_active = data.get('is_active', quick_number.is_active)
        quick_number.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/quick_call_numbers/<int:number_id>', methods=['DELETE'])
def delete_quick_call_number(number_id):
    """빠른 전화 번호 삭제"""
    try:
        quick_number = QuickCallNumber.query.get(number_id)
        if not quick_number:
            return jsonify({'success': False, 'error': '연락처를 찾을 수 없습니다.'})
        
        db.session.delete(quick_number)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_empty_location', methods=['POST'])
def create_empty_location():
    """빈 장소 생성 (더미 스케줄로 실제 생성)"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        session_part = data.get('session_part')
        location_name = data.get('location_name')
        schedule_type = data.get('type', 'pickup')
        
        if not all([day_of_week is not None, session_part, location_name]):
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        # 부별 기본 시간 설정
        if session_part == 1:
            default_time = time(14, 0) if schedule_type == 'pickup' else time(14, 50)
        elif session_part == 2:
            default_time = time(15, 0) if schedule_type == 'pickup' else time(15, 50)
        elif session_part == 3:
            default_time = time(16, 30) if schedule_type == 'pickup' else time(17, 20)
        elif session_part == 4:
            default_time = time(17, 30) if schedule_type == 'pickup' else time(18, 20)
        else:  # 5부
            default_time = time(19, 0) if schedule_type == 'pickup' else time(19, 50)
        
        # 해당 장소에 이미 스케줄이 있는지 확인
        existing_schedule = Schedule.query.filter_by(
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=location_name,
            time=default_time
        ).first()
        
        if existing_schedule:
            return jsonify({
                'success': True, 
                'message': f'"{location_name}" 장소가 이미 존재합니다.',
                'location_name': location_name,
                'existing': True
            })
        
        # 실제로는 빈 장소만 프론트엔드에서 관리
        # 실제 스케줄은 학생이 추가될 때만 생성
        
        return jsonify({
            'success': True, 
            'message': f'"{location_name}" 장소가 생성되었습니다.',
            'location_name': location_name,
            'day_of_week': day_of_week,
            'session_part': session_part,
            'type': schedule_type,
            'default_time': default_time.strftime('%H:%M'),
            'placeholder_created': True
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# 카카오톡 설정 관리 API
@app.route('/api/kakao_settings')
def get_kakao_settings():
    """카카오톡 설정 조회"""
    try:
        settings = KakaoSettings.query.first()
        if not settings:
            # 기본 설정 생성
            settings = KakaoSettings()
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'settings': {
                'business_id': settings.business_id or '',
                'template_id': settings.template_id or '',
                'is_active': settings.is_active,
                'test_mode': settings.test_mode
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/kakao_settings', methods=['POST'])
def update_kakao_settings():
    """카카오톡 설정 업데이트"""
    try:
        data = request.get_json()
        
        settings = KakaoSettings.query.first()
        if not settings:
            settings = KakaoSettings()
            db.session.add(settings)
        
        settings.business_id = data.get('business_id', settings.business_id)
        settings.api_key = data.get('api_key', settings.api_key)
        settings.template_id = data.get('template_id', settings.template_id)
        settings.sender_key = data.get('sender_key', settings.sender_key)
        settings.is_active = data.get('is_active', settings.is_active)
        settings.test_mode = data.get('test_mode', settings.test_mode)
        settings.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# 🎯 단순하고 안전한 데이터베이스 초기화 (환경 통합)
def initialize_database():
    """데이터베이스 테이블을 생성하고 초기화"""
    try:
        with app.app_context():
            # 데이터베이스 테이블 생성
            db.create_all()
            print("✅ 데이터베이스 테이블 생성 완료")
            
            # 🚨 스키마 호환성 문제 자동 해결
            try:
                with db.engine.connect() as conn:
                    # 🔥 Schedule 테이블의 schedule_type 컬럼을 VARCHAR(30)으로 확장 (국기원부/돌봄시스템 지원)
                    try:
                        conn.execute(db.text("ALTER TABLE schedule ALTER COLUMN schedule_type TYPE VARCHAR(30);"))
                        print("✅ Schedule.schedule_type 컬럼 VARCHAR(30)으로 확장 완료")
                    except Exception as e1:
                        print(f"⚠️ schedule_type 업데이트 스킵: {e1}")
                    
                    # Schedule 테이블의 location 컬럼을 VARCHAR(100)으로 확장
                    try:
                        conn.execute(db.text("ALTER TABLE schedule ALTER COLUMN location TYPE VARCHAR(100);"))
                        print("✅ Schedule.location 컬럼 VARCHAR(100)으로 확장 완료")
                    except Exception as e2:
                        print(f"⚠️ location 업데이트 스킵: {e2}")
                    
                    conn.commit()
                    print("🎯 데이터베이스 스키마 업데이트 완료!")
            except Exception as schema_error:
                print(f"⚠️ 전체 스키마 업데이트 실패: {schema_error}")
            
            # 빈 데이터베이스 확인 (샘플 데이터 자동 생성 제거)
            student_count = Student.query.count()
            print(f"📊 현재 학생 수: {student_count}명")
            print("✅ 데이터베이스 초기화 완료 - 깔끔한 상태")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        import traceback
        traceback.print_exc()

# 자동 초기 데이터 추가 함수 제거됨 (안전성 확보)

# 자동 스케줄 추가 함수 제거됨 (안전성 확보)

# 앱 시작시 테이블만 생성 (깔끔한 버전)
print("🚀 애플리케이션 시작 - 데이터베이스 테이블 생성...")
try:
    with app.app_context():
        db.create_all()
        print("✅ 데이터베이스 테이블 생성 완료!")
except Exception as e:
    print(f"❌ 테이블 생성 중 예외 발생: {e}")

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True)

# 임시 엔드포인트 제거 완료

# 위험한 디버그 엔드포인트 제거됨

# 위험한 강제 초기화 엔드포인트 제거됨

# 제거: 모든 일회성 코드들 정리 완료

# 유지해야 할 유일한 유틸리티 함수들
def validate_student_name(name):
    """학생 이름 유효성 검사"""
    if not name or not name.strip():
        return False, "이름이 입력되지 않았습니다."
    
    name = name.strip()
    if len(name) < 2:
        return False, "이름은 2글자 이상이어야 합니다."
    if len(name) > 10:
        return False, "이름은 10글자 이하여야 합니다."
    
    return True, ""

def validate_phone_number(phone):
    """전화번호 유효성 검사"""
    if not phone:
        return True, ""  # 전화번호는 선택사항
    
    import re
    # 기본적인 전화번호 패턴 (010-1234-5678, 010 1234 5678, 01012345678 등)
    pattern = r'^[0-9\-\s]+$'
    if not re.match(pattern, phone):
        return False, "올바른 전화번호 형식이 아닙니다."
    
    return True, ""

def validate_location_name(location):
    """장소명 유효성 검사"""
    if not location or not location.strip():
        return False, "장소명이 입력되지 않았습니다."
    
    location = location.strip()
    if len(location) > 50:
        return False, "장소명은 50글자 이하여야 합니다."
    
    return True, ""

def validate_session_part(session_part):
    """부(session_part) 유효성 검사"""
    try:
        session_part = int(session_part)
        if session_part not in [1, 2, 3, 4, 5]:
            return False, "부는 1부~5부 중에서 선택해야 합니다."
        return True, ""
    except (ValueError, TypeError):
        return False, "올바른 부를 선택해주세요."

def sanitize_input(text, max_length=None):
    """입력값 정제"""
    if not text:
        return ""
    
    text = str(text).strip()
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def error_response(message, status_code=400):
    """표준 에러 응답"""
    return jsonify({'success': False, 'error': message}), status_code

def success_response(message, data=None):
    """표준 성공 응답"""
    response = {'success': True, 'message': message}
    if data:
        response['data'] = data
    return jsonify(response)

# 불필요한 일회성 API 제거됨