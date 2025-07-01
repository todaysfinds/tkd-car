# -*- coding: utf-8 -*-
"""
태권도 운송 관리 시스템
Python 3.11.8 전용
"""
import sys
print(f"🐍 Python 버전: {sys.version}")

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
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
    # 프로덕션 환경 플래그 설정
    app.config['IS_LOCAL_DEV'] = False
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
        # 로컬 PostgreSQL 환경 플래그 설정
        app.config['IS_LOCAL_DEV'] = True
    except:
        # 로컬에서 PostgreSQL 없으면 환경변수 사용
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tkd_transport.db'
        print("🗄️ 로컬 개발용 SQLite - ⚠️ 배포사이트와 다른 DB!")
        # 로컬 환경 플래그 설정
        app.config['IS_LOCAL_DEV'] = True

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
    is_private_car = db.Column(db.Boolean, default=False)  # 개인차량 여부
    memo = db.Column(db.String(200))  # 메모 필드 추가
    # 안심번호 서비스용 필드
    allow_contact = db.Column(db.Boolean, default=True)  # 연락 허용 여부
    contact_preference = db.Column(db.String(20), default='phone')  # phone, kakao, both
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=월요일, 6=일요일
    schedule_type = db.Column(db.String(30), nullable=False)  # 'pickup', 'dropoff', 'care_system', 'national_training'
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
    description = db.Column(db.String(200))  # 장소 설명
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 라우트
@app.route('/')
def index():
    return redirect(url_for('schedule'))

@app.route('/today')
def today():
    # 기존 today 경로는 schedule로 리다이렉트
    return redirect(url_for('schedule'))



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

@app.route('/schedule')
def schedule():
    # 승차/하차 완전 분리 구조
    schedule_data = {}
    
    # 🚨 로컬 개발 환경 경고 표시
    is_local_dev = app.config.get('IS_LOCAL_DEV', False)
    
    # 모든 스케줄 조회 (더미 학생 제외)
    schedules = db.session.query(Student, Schedule).join(Schedule).filter(
        ~Student.name.like('_PH_%')  # 더미 학생 제외
    ).order_by(
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
            # 🚨 중요: Schedule.location을 최우선으로 사용 (폴백 최소화)
            if schedule.location:
                location = schedule.location
            else:
                # Schedule.location이 없을 때만 Student.pickup_location 사용
                location = student.pickup_location or f'미정_{student.id}'  # 학생별 고유 미정 장소
        
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
    
    # 🎯 더미 스케줄로 생성된 빈 장소들 추가 (실제 학생 없는 장소) - 시간대별 독립적
    dummy_schedules = db.session.query(Student, Schedule).join(Schedule).filter(
        Student.name.like('_PH_%')  # 더미 학생만 조회
    ).all()
    
    for dummy_student, dummy_schedule in dummy_schedules:
        day = dummy_schedule.day_of_week
        schedule_type = dummy_schedule.schedule_type
        location = dummy_schedule.location
        schedule_time = dummy_schedule.time  # 🔥 시간 정보 추가
        
        if schedule_type in ['pickup', 'dropoff']:
            part = dummy_student.session_part or 1
            
            # 해당 장소에 실제 학생이 있는지 확인 (🎯 시간대별 독립적 체크)
            has_real_students = False
            if (day in schedule_data and 
                part in schedule_data[day] and 
                schedule_type in schedule_data[day][part] and 
                location in schedule_data[day][part][schedule_type]):
                
                # 실제 학생 데이터 중에서 같은 시간대 확인
                for student_data in schedule_data[day][part][schedule_type][location]:
                    if student_data['schedule'].time == schedule_time:
                        has_real_students = True
                        break
            
            if has_real_students:
                # 실제 학생이 같은 시간대에 있으면 더미는 추가하지 않음
                continue
            
            # 빈 장소 구조 초기화
            if day not in schedule_data:
                schedule_data[day] = {}
            if part not in schedule_data[day]:
                schedule_data[day][part] = {}
            if schedule_type not in schedule_data[day][part]:
                schedule_data[day][part][schedule_type] = {}
            
            # 🎯 시간 관련 코드 완전 제거 - 시간대별 고유 키 제거
            if location not in schedule_data[day][part][schedule_type]:
                schedule_data[day][part][schedule_type][location] = []
                print(f"   📍 빈 장소 추가: {location} - {day}요일 {part}부 {schedule_type}")
    
    # 현재 요일 (0=월요일, 6=일요일)
    current_day = datetime.now().weekday()
    
    return render_template('schedule.html', 
                         schedule_data=schedule_data, 
                         current_day=current_day,
                         day_names=['월', '화', '수', '목', '금', '토', '일'],
                         is_local_dev=is_local_dev)

@app.route('/admin/students')
def admin_students():
    # 더미 학생 제외
    students = Student.query.filter(
        ~Student.name.like('_PH_%')
    ).order_by(Student.name).all()
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
    # 장소별로 학생들을 그룹화 (더미 학생 제외)
    students = Student.query.filter(
        ~Student.name.like('_PH_%')
    ).all()
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
        
        print(f"   - 장소명: {name}")
        
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
            name=name
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
    """🚨 위험: 장소관리 페이지에서의 전역적 장소명 변경 - 사용 금지"""
    try:
        data = request.get_json()
        original_name = data.get('original_name')
        new_name = data.get('new_name')
        
        if not original_name or not new_name:
            return jsonify({'success': False, 'message': '장소명이 필요합니다.'})
        
        # 🚨 전역 변경 경고 및 차단
        print(f"🚨 위험한 전역 장소명 변경 시도 차단: '{original_name}' → '{new_name}'")
        
        return jsonify({
            'success': False, 
            'message': '⚠️ 전역 장소명 변경은 데이터 오염 위험으로 인해 차단되었습니다.\n\n대신 다음을 사용하세요:\n- 스케줄 페이지에서 요일별 독립적 수정\n- 관리자에게 문의하여 안전한 방법으로 변경',
            'warning': 'GLOBAL_CHANGE_BLOCKED'
        })
        
        # 아래 코드는 실행되지 않음 (안전을 위해 주석 처리)
        """
        # Location 테이블 업데이트
        location = Location.query.filter_by(name=original_name).first()
        if location:
            location.name = new_name
        
        # 해당 장소의 모든 학생들 업데이트 (전역적 변경)
        students = Student.query.filter_by(pickup_location=original_name).all()
        for student in students:
            student.pickup_location = new_name
        
        # Schedule 테이블의 모든 해당 장소도 업데이트 (전역적 변경)
        schedules = Schedule.query.filter_by(location=original_name).all()
        for schedule in schedules:
            schedule.location = new_name
        
        db.session.commit()
        
        print(f"✅ 장소명 전역 변경 완료: {len(students)}명 학생, {len(schedules)}개 스케줄 업데이트")
        return jsonify({'success': True})
        """
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
        session_part = data.get('session_part')
        memo = data.get('memo')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': '학생을 찾을 수 없습니다.'})
        
        if name:
            student.name = name
        student.pickup_location = location if location else None
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
        # 더미 학생 제외
        students = Student.query.filter(
            ~Student.name.like('_PH_%')
        ).order_by(Student.name).all()
        
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
    """개별 학생을 특정 스케줄에 추가 (중복 체크, 시간대 분기, session_part 등 완전 제거)"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('schedule_type')
        target_location = data.get('location')

        if not all([student_id, day_of_week is not None, schedule_type, target_location]):
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})

        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})

        new_schedule = Schedule(
            student_id=student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=target_location
        )
        db.session.add(new_schedule)
        db.session.commit()
        return jsonify({'success': True, 'message': '학생이 추가되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_multiple_students_to_schedule', methods=['POST'])
def add_multiple_students_to_schedule():
    """여러 학생을 한 번에 특정 스케줄에 추가 (중복 체크, 시간대 분기, session_part 등 완전 제거)"""
    try:
        data = request.get_json()
        students = data.get('students', [])
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('schedule_type')
        target_location = data.get('location')

        if not all([students, day_of_week is not None, schedule_type, target_location]):
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})

        added_students = []
        for student_data in students:
            student_id = student_data.get('id')
            student = Student.query.get(student_id)
            if not student:
                continue
            new_schedule = Schedule(
                student_id=student_id,
                day_of_week=day_of_week,
                schedule_type=schedule_type,
                location=target_location
            )
            db.session.add(new_schedule)
            added_students.append({'id': student_id, 'name': student.name})
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(added_students)}명의 학생이 추가되었습니다.', 'added_students': added_students})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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

@app.route('/api/update_location_in_schedule', methods=['POST'])
def update_location_in_schedule():
    """스케줄에서 장소명 변경 (돌봄시스템/국기원부)"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        old_location = data.get('old_location')
        new_location = data.get('new_location')
        location_type = data.get('location_type')
        
        print(f"🔄 장소명 변경: {old_location} → {new_location} (day={day_of_week}, type={location_type})")
        
        # 스케줄 타입 결정
        schedule_type = 'care_system' if location_type == 'care_system' else 'national_training'
        
        # 접미사 패턴 정의
        if location_type == 'care_system':
            # 돌봄시스템: _care1, _care2, _care3
            suffixes = ['_care1', '_care2', '_care3']
        else:
            # 국기원부: _national
            suffixes = ['_national']
        
        updated_count = 0
        
        # 각 접미사별로 스케줄 찾기 및 업데이트
        for suffix in suffixes:
            old_full_location = f"{old_location}{suffix}"
            new_full_location = f"{new_location}{suffix}"
            
            # 정확히 일치하는 location 찾기
            schedules = Schedule.query.filter_by(
                day_of_week=day_of_week,
                schedule_type=schedule_type,
                location=old_full_location
            ).all()
            
            for schedule in schedules:
                schedule.location = new_full_location
                updated_count += 1
                print(f"  ✅ 변경: {old_full_location} → {new_full_location}")
        
        db.session.commit()
        
        print(f"✅ {updated_count}개 스케줄의 장소명 변경 완료")
        
        return jsonify({
            'success': True,
            'message': f'장소명이 변경되었습니다. ({updated_count}개 스케줄 업데이트)',
            'updated_count': updated_count
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 장소명 변경 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_location_from_schedule', methods=['POST'])
def delete_location_from_schedule():
    """스케줄에서 장소 삭제 (돌봄시스템/국기원부)"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        location = data.get('location')
        location_type = data.get('location_type')
        
        print(f"🗑️ 장소 삭제: {location} (day={day_of_week}, type={location_type})")
        
        # 스케줄 타입 결정
        schedule_type = 'care_system' if location_type == 'care_system' else 'national_training'
        
        # 접미사 패턴 정의
        if location_type == 'care_system':
            # 돌봄시스템: _care1, _care2, _care3
            suffixes = ['_care1', '_care2', '_care3']
        else:
            # 국기원부: _national
            suffixes = ['_national']
        
        deleted_count = 0
        student_names = []
        
        # 각 접미사별로 스케줄 찾기 및 삭제
        for suffix in suffixes:
            full_location = f"{location}{suffix}"
            
            # 정확히 일치하는 location 찾기
            schedules = Schedule.query.filter_by(
                day_of_week=day_of_week,
                schedule_type=schedule_type,
                location=full_location
            ).all()
            
            for schedule in schedules:
                student_names.append(schedule.student.name)
                print(f"  🗑️ 삭제: {full_location} - {schedule.student.name}")
                db.session.delete(schedule)
                deleted_count += 1
        
        db.session.commit()
        
        print(f"✅ {deleted_count}개 스케줄 삭제 완료: {', '.join(student_names)}")
        
        return jsonify({
            'success': True,
            'message': f'"{location}" 장소가 삭제되었습니다. ({deleted_count}명의 학생 제거)',
            'deleted_count': deleted_count,
            'student_names': student_names
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 장소 삭제 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_pickup_location', methods=['POST'])
def update_pickup_location():
    """승차/하차 장소명 변경 (요일별 독립적)"""
    try:
        data = request.get_json()
        old_location = data.get('old_location')
        new_location = data.get('new_location')
        day_of_week = data.get('day_of_week')  # 요일 정보 추가 필수
        
        if day_of_week is None:
            return jsonify({'success': False, 'error': 'day_of_week 파라미터가 필요합니다.'})
        
        print(f"🔄 승차/하차 장소명 변경: {old_location} → {new_location} (요일: {day_of_week})")
        
        # ⚠️ Location 테이블은 건드리지 않음 (참조용만 유지)
        # 전역 Location 테이블을 수정하면 모든 요일에 영향을 줌
        
        # ⚠️ Student 테이블도 건드리지 않음 (기본 장소 정보만 유지)
        # pickup_location은 학생의 기본 장소 정보로만 사용
        
        # 🎯 Schedule 테이블의 해당 요일만 변경
        schedules = Schedule.query.filter(
            Schedule.schedule_type.in_(['pickup', 'dropoff']),
            Schedule.location == old_location,
            Schedule.day_of_week == day_of_week  # 요일별 구분 추가!
        ).all()
        
        updated_schedule_count = 0
        for schedule in schedules:
            schedule.location = new_location
            updated_schedule_count += 1
        
        db.session.commit()
        
        print(f"✅ 장소명 변경 완료: {day_of_week}요일 스케줄 {updated_schedule_count}개")
        
        return jsonify({
            'success': True,
            'message': f'{day_of_week}요일 "{old_location}" 장소가 "{new_location}"으로 변경되었습니다.',
            'updated_schedules': updated_schedule_count,
            'day_affected': day_of_week
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 승차/하차 장소명 변경 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_pickup_location', methods=['POST'])
def delete_pickup_location():
    """승차/하차 장소 삭제 (요일별 독립적)"""
    try:
        data = request.get_json()
        location_name = data.get('location_name')
        day_of_week = data.get('day_of_week')  # 요일 정보 추가 필수
        
        if day_of_week is None:
            return jsonify({'success': False, 'error': 'day_of_week 파라미터가 필요합니다.'})
        
        print(f"🗑️ 승차/하차 장소 삭제: {location_name} (요일: {day_of_week})")
        
        # ⚠️ Location 테이블은 건드리지 않음 (다른 요일에서 사용할 수 있음)
        # 전역 Location 테이블을 삭제하면 모든 요일에 영향을 줌
        
        # ⚠️ Student 테이블도 건드리지 않음 (기본 장소 정보만 유지)
        # pickup_location은 학생의 기본 장소 정보로만 사용
        
        # 🎯 Schedule 테이블의 해당 요일만 삭제
        schedules = Schedule.query.filter(
            Schedule.schedule_type.in_(['pickup', 'dropoff']),
            Schedule.location == location_name,
            Schedule.day_of_week == day_of_week  # 요일별 구분 추가!
        ).all()
        
        deleted_schedule_count = 0
        student_names = []
        for schedule in schedules:
            student_names.append(schedule.student.name)
            db.session.delete(schedule)
            deleted_schedule_count += 1
        
        db.session.commit()
        
        print(f"✅ 장소 삭제 완료: {day_of_week}요일 스케줄 {deleted_schedule_count}개")
        
        return jsonify({
            'success': True,
            'message': f'{day_of_week}요일 "{location_name}" 장소가 삭제되었습니다.',
            'deleted_schedules': deleted_schedule_count,
            'student_names': student_names,
            'day_affected': day_of_week
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ 승차/하차 장소 삭제 오류: {str(e)}")
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
🎯 수업: {student.session_part}부

차량이 곧 도착할 예정입니다.
준비해주세요!

🏫 OO태권도장
''',
        'arrival': f'''
🏫 도장 도착 알림

{student.name} 학생이 안전하게 도장에 도착했습니다.

🎯 수업: {student.session_part}부

수업 후 하차 시간을 별도로 안내드리겠습니다.

🏫 OO태권도장
''',
        'departure': f'''
🚌 하차 출발 알림

{student.name} 학생이 수업을 마치고 하차를 위해 출발했습니다.

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

@app.route('/api/cleanup_duplicates', methods=['POST'])
def cleanup_duplicates():
    """중복 스케줄 정리 (관리자용)"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        location = data.get('location')
        schedule_type = data.get('schedule_type', 'pickup')
        
        if day_of_week is None or not location:
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        print(f"🧹 중복 정리: day={day_of_week}, location='{location}', type={schedule_type}")
        
        # 해당 조건의 모든 스케줄 찾기
        schedules = Schedule.query.filter_by(
            day_of_week=day_of_week,
            location=location,
            schedule_type=schedule_type
        ).all()
        
        print(f"   📋 발견된 스케줄: {len(schedules)}개")
        
        # 학생별로 그룹화
        student_schedules = {}
        for schedule in schedules:
            student_id = schedule.student_id
            if student_id not in student_schedules:
                student_schedules[student_id] = []
            student_schedules[student_id].append(schedule)
        
        # 중복 제거
        removed_count = 0
        for student_id, sch_list in student_schedules.items():
            if len(sch_list) > 1:
                student = Student.query.get(student_id)
                print(f"   🔍 {student.name} 중복 {len(sch_list)}개 발견")
                
                # 첫 번째만 남기고 나머지 삭제
                for schedule in sch_list[1:]:
                    print(f"      - 삭제: {schedule.id}")
                    db.session.delete(schedule)
                    removed_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{removed_count}개의 중복 스케줄이 정리되었습니다.',
            'removed_count': removed_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 중복 정리 에러: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_empty_location', methods=['POST'])
def create_empty_location():
    """빈 장소 생성 (실제 더미 스케줄 생성으로 지속성 보장) - 🎯 돌봄시스템/국기원부 지원"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        session_part = data.get('session_part')
        location_name = data.get('location_name')
        schedule_type = data.get('type', 'pickup')
        
        print(f"🏗️ 빈 장소 생성 요청: {location_name} (day={day_of_week}, part={session_part}, type={schedule_type})")
        print(f"   - 받은 데이터: {data}")
        print(f"   - day_of_week 타입: {type(day_of_week)}, 값: {day_of_week}")
        print(f"   - session_part 타입: {type(session_part)}, 값: {session_part}")
        print(f"   - location_name 타입: {type(location_name)}, 값: {location_name}")
        print(f"   - schedule_type 타입: {type(schedule_type)}, 값: {schedule_type}")
        
        if not all([day_of_week is not None, session_part, location_name]):
            print(f"❌ 필수 정보 누락 체크: day_of_week={day_of_week is not None}, session_part={bool(session_part)}, location_name={bool(location_name)}")
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        # 🎯 돌봄시스템/국기원부 타입 자동 감지 및 보정
        if session_part in [6, 8, 9]:  # 돌봄시스템 A/B/C
            schedule_type = 'care_system'
            print(f"   🏫 돌봄시스템 감지: session_part={session_part} → type=care_system")
        elif session_part == 7:  # 국기원부
            schedule_type = 'national_training'
            print(f"   🏛️ 국기원부 감지: session_part={session_part} → type=national_training")
        
        # 부별 기본 시간 설정 (🎯 돌봄시스템과 국기원부 포함)
        # 🎯 시간 관련 코드 완전 제거 - 시간대별 기본 시간 설정 삭제
        
        # 🎯 최종 장소명 결정 (돌봄시스템/국기원부는 접미사 추가)
        if schedule_type == 'care_system':
            # 돌봄시스템별 접미사 추가
            if session_part == 6:
                final_location_name = f"{location_name}_care1"
            elif session_part == 8:
                final_location_name = f"{location_name}_care2"
            elif session_part == 9:
                final_location_name = f"{location_name}_care3"
            else:
                final_location_name = f"{location_name}_care1"
            print(f"   🏫 돌봄시스템 장소명: {location_name} → {final_location_name}")
        elif schedule_type == 'national_training':
            final_location_name = f"{location_name}_national"
            print(f"   🏛️ 국기원부 장소명: {location_name} → {final_location_name}")
        else:
            final_location_name = location_name
            print(f"   📍 일반 장소명: {final_location_name}")
        
        # 해당 장소에 이미 스케줄이 있는지 확인 (🎯 시간 관련 코드 완전 제거)
        existing_schedule = Schedule.query.filter_by(
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=final_location_name  # 🔥 최종 장소명 사용!
        ).first()
        
        if existing_schedule:
            print(f"📍 동일 장소 이미 존재: {final_location_name}")
            return jsonify({
                'success': True, 
                'message': f'"{location_name}" 장소가 이미 존재합니다.',
                'location_name': location_name,
                'existing': True
            })
        
        # 🎯 실제 더미 학생으로 장소 생성 (새로고침 후에도 유지됨)  
        # 더미 학생 생성 (이름 길이 제한으로 해시 사용)
        import hashlib
        hash_input = f"{final_location_name}_{day_of_week}_{session_part}_{schedule_type}"
        location_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        dummy_student_name = f"_PH_{location_hash}"
        
        print(f"   - 해시 입력: {hash_input}")
        print(f"   - 더미 학생명: {dummy_student_name}")
        
        # 더미 학생이 이미 있는지 확인
        existing_dummy = Student.query.filter(Student.name.like('_PH_%')).filter_by(name=dummy_student_name).first()
        print(f"   - 기존 더미 학생: {existing_dummy.name if existing_dummy else 'None'}")
        
        if not existing_dummy:
            # 더미 학생 생성
            print(f"   - 새 더미 학생 생성 중...")
            dummy_student = Student(
                name=dummy_student_name,
                grade="PLACEHOLDER",
                session_part=session_part,
                pickup_location=final_location_name,  # 🔥 최종 장소명 사용!
                memo=f"빈장소:{location_name}({day_of_week}요일{session_part}부{schedule_type})"
            )
            db.session.add(dummy_student)
            db.session.flush()  # ID 생성을 위해 flush
            
            # 🚨 중요: flush 후 student_id 검증
            if not dummy_student.id:
                raise Exception("더미 학생 ID 생성 실패")
            
            dummy_student_id = dummy_student.id
            print(f"   - 더미 학생 생성 완료: ID={dummy_student_id}")
        else:
            dummy_student_id = existing_dummy.id
            print(f"   - 기존 더미 학생 재사용: ID={dummy_student_id}")
        
        # 🚨 최종 student_id 검증
        if not dummy_student_id:
            raise Exception(f"유효하지 않은 student_id: {dummy_student_id}")
        
        # 더미 스케줄 생성
        print(f"   - 더미 스케줄 생성 중... (student_id={dummy_student_id})")
        
        # 🚨 student_id 재검증
        if not dummy_student_id or dummy_student_id <= 0:
            raise Exception(f"잘못된 student_id: {dummy_student_id}")
        
        dummy_schedule = Schedule(
            student_id=dummy_student_id,
            day_of_week=day_of_week,
            schedule_type=schedule_type,
            location=final_location_name  # 🔥 최종 장소명 사용!
        )
        
        db.session.add(dummy_schedule)
        
        # 🚨 스케줄 추가 전 한번 더 flush
        db.session.flush()
        
        # 🚨 스케줄 ID 검증
        if not dummy_schedule.id:
            raise Exception("더미 스케줄 ID 생성 실패")
        
        print(f"   - DB 커밋 중... (스케줄 ID: {dummy_schedule.id})")
        db.session.commit()
        print(f"   - DB 커밋 완료!")
        
        print(f"✅ 빈 장소 생성 완료: {final_location_name} (더미 스케줄 ID: {dummy_schedule.id})")
        
        return jsonify({
            'success': True, 
            'message': f'"{location_name}" 장소가 생성되었습니다.',
            'location_name': location_name,
            'final_location_name': final_location_name,  # 🔥 디버깅용 추가
            'day_of_week': day_of_week,
            'session_part': session_part,
            'type': schedule_type,
            'dummy_created': True
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 빈 장소 생성 실패: {str(e)}")
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
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

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

@app.route('/api/admin/fix_duplicate_schedules', methods=['POST'])
def fix_duplicate_schedules():
    """🚨 관리자 전용: 중복 스케줄 정리"""
    try:
        data = request.get_json()
        student_name = data.get('student_name')
        
        if not student_name:
            return jsonify({'success': False, 'error': '학생 이름이 필요합니다.'})
        
        print(f"🔍 중복 스케줄 정리 시작: {student_name}")
        
        # 해당 학생의 모든 스케줄 조회
        student = Student.query.filter_by(name=student_name).first()
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        schedules = Schedule.query.filter_by(student_id=student.id).all()
        
        # 중복 찾기: (요일, 시간대, 승차/하차, 장소) 조합별로 그룹화
        schedule_groups = {}
        for schedule in schedules:
            key = (schedule.day_of_week, schedule.schedule_time, schedule.schedule_type, schedule.location)
            if key not in schedule_groups:
                schedule_groups[key] = []
            schedule_groups[key].append(schedule)
        
        # 중복 제거
        removed_count = 0
        duplicate_info = []
        
        for key, group in schedule_groups.items():
            if len(group) > 1:
                # 첫 번째만 남기고 나머지 삭제
                day, time, type_, location = key
                duplicate_info.append({
                    'day': day,
                    'time': str(time),
                    'type': type_,
                    'location': location,
                    'duplicate_count': len(group)
                })
                
                # 첫 번째 제외하고 삭제
                for schedule in group[1:]:
                    db.session.delete(schedule)
                    removed_count += 1
                    print(f"🗑️ 중복 스케줄 삭제: {day}요일 {time} {type_} {location}")
        
        db.session.commit()
        
        print(f"✅ 중복 스케줄 정리 완료: {removed_count}개 삭제")
        
        return jsonify({
            'success': True,
            'message': f'{student_name} 학생의 중복 스케줄 {removed_count}개를 정리했습니다.',
            'removed_count': removed_count,
            'duplicate_info': duplicate_info
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 중복 스케줄 정리 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/fix_location_consistency', methods=['POST'])
def fix_location_consistency():
    """🚨 관리자 전용: 장소 정보 일관성 복구"""
    try:
        data = request.get_json()
        target_location = data.get('target_location')
        correct_location = data.get('correct_location')
        day_of_week = data.get('day_of_week')  # 특정 요일만 수정 (선택사항)
        
        if not target_location or not correct_location:
            return jsonify({'success': False, 'error': '대상 장소명과 올바른 장소명이 필요합니다.'})
        
        print(f"🔧 장소 정보 일관성 복구: '{target_location}' → '{correct_location}'")
        if day_of_week is not None:
            print(f"   - 대상 요일: {day_of_week}")
        
        # Schedule 테이블에서 해당 장소 찾기
        query = Schedule.query.filter(Schedule.location == target_location)
        if day_of_week is not None:
            query = query.filter(Schedule.day_of_week == day_of_week)
        
        schedules = query.all()
        
        updated_count = 0
        affected_students = set()
        
        for schedule in schedules:
            schedule.location = correct_location
            affected_students.add(schedule.student.name)
            updated_count += 1
            print(f"   ✅ 수정: {schedule.student.name} - {schedule.day_of_week}요일 {schedule.schedule_type}")
        
        # 🚨 Student 테이블의 pickup_location은 건드리지 않음
        # 기본 장소 정보는 그대로 유지하고 스케줄만 수정
        
        db.session.commit()
        
        print(f"✅ 장소 정보 일관성 복구 완료: {updated_count}개 스케줄, {len(affected_students)}명 학생")
        
        return jsonify({
            'success': True,
            'message': f'장소 정보 일관성이 복구되었습니다.\n- 수정된 스케줄: {updated_count}개\n- 영향받은 학생: {len(affected_students)}명',
            'updated_count': updated_count,
            'affected_students': list(affected_students),
            'day_affected': day_of_week
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 장소 정보 일관성 복구 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/diagnose_schedule_data', methods=['POST'])
def diagnose_schedule_data():
    """🔍 관리자 전용: 스케줄 데이터 진단"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        session_part = data.get('session_part')
        
        print(f"🔍 스케줄 데이터 진단 시작 (요일: {day_of_week}, 부: {session_part})")
        
        # 해당 요일/부의 모든 스케줄 조회
        query = Schedule.query.join(Student).filter(
            ~Student.name.like('_PH_%')  # 더미 학생 제외
        )
        
        if day_of_week is not None:
            query = query.filter(Schedule.day_of_week == day_of_week)
        
        if session_part is not None:
            query = query.filter(Student.session_part == session_part)
        
        schedules = query.all()
        
        # 문제 진단
        issues = []
        location_groups = {}
        
        for schedule in schedules:
            student = schedule.student
            
            # 장소별 그룹화
            location = schedule.location or student.pickup_location or f'미정_{student.id}'
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append({
                'student_name': student.name,
                'student_id': student.id,
                'schedule_location': schedule.location,
                'student_pickup_location': student.pickup_location,
                'schedule_type': schedule.schedule_type,
                'schedule_time': str(schedule.time)
            })
            
            # 문제 체크
            if not schedule.location and not student.pickup_location:
                issues.append(f"⚠️ {student.name}: 스케줄과 학생 모두 장소 정보 없음")
            elif not schedule.location:
                issues.append(f"📍 {student.name}: 스케줄 장소 정보 없음 (학생 기본 장소: {student.pickup_location})")
            elif schedule.location != student.pickup_location:
                issues.append(f"🔄 {student.name}: 스케줄 장소({schedule.location}) ≠ 학생 기본 장소({student.pickup_location})")
        
        # 중복 장소에 있는 학생들 체크
        for location, students in location_groups.items():
            if len(students) > 1:
                student_names = [s['student_name'] for s in students]
                issues.append(f"👥 {location}: {len(students)}명 학생 ({', '.join(student_names)})")
        
        print(f"✅ 진단 완료: {len(schedules)}개 스케줄, {len(issues)}개 문제 발견")
        
        return jsonify({
            'success': True,
            'total_schedules': len(schedules),
            'location_groups': location_groups,
            'issues': issues,
            'issue_count': len(issues)
        })
        
    except Exception as e:
        print(f"❌ 스케줄 데이터 진단 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create_empty_care_location', methods=['POST'])
def create_empty_care_location():
    """돌봄시스템 빈 장소 생성 전용 API"""
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week')
        care_type = data.get('care_type')  # care1, care2, care3
        location_name = data.get('location_name')
        
        print(f"🏫 돌봄시스템 빈 장소 생성: {location_name} (day={day_of_week}, care_type={care_type})")
        
        # 🎯 careType별로 다른 session_part 할당
        if care_type == 'care1':
            session_part = 6  # 돌봄시스템 A
        elif care_type == 'care2':
            session_part = 8  # 돌봄시스템 B
        elif care_type == 'care3':
            session_part = 9  # 돌봄시스템 C
        else:
            return jsonify({'success': False, 'error': '잘못된 돌봄시스템 타입입니다.'})
        
        if not all([day_of_week is not None, care_type, location_name]):
            return jsonify({'success': False, 'error': '필수 정보가 누락되었습니다.'})
        
        # 🎯 시간 관련 코드 완전 제거 - 돌봄시스템별 기본 시간 설정 삭제
        
        # 장소명에 care_type 접미사 추가
        final_location_name = f"{location_name}_{care_type}"
        
        # 해당 장소에 이미 스케줄이 있는지 확인
        existing_schedule = Schedule.query.filter_by(
            day_of_week=day_of_week,
            schedule_type='care_system',
            location=final_location_name
        ).first()
        
        if existing_schedule:
            print(f"📍 돌봄시스템 장소 이미 존재: {final_location_name}")
            return jsonify({
                'success': True, 
                'message': f'"{location_name}" 장소가 이미 존재합니다.',
                'location_name': location_name,
                'existing': True
            })
        
        # 🎯 더미 학생으로 장소 생성
        import hashlib
        hash_input = f"{final_location_name}_{day_of_week}_{session_part}_care_system"
        location_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        dummy_student_name = f"_PH_{location_hash}"
        
        # 더미 학생이 이미 있는지 확인
        existing_dummy = Student.query.filter(Student.name.like('_PH_%')).filter_by(name=dummy_student_name).first()
        
        if not existing_dummy:
            # 더미 학생 생성
            dummy_student = Student(
                name=dummy_student_name,
                grade="PLACEHOLDER",
                session_part=session_part,
                pickup_location=final_location_name,
                memo=f"빈장소:{location_name}({day_of_week}요일{care_type}돌봄시스템)"
            )
            db.session.add(dummy_student)
            db.session.flush()
            dummy_student_id = dummy_student.id
        else:
            dummy_student_id = existing_dummy.id
        
        # 더미 스케줄 생성
        dummy_schedule = Schedule(
            student_id=dummy_student_id,
            day_of_week=day_of_week,
            schedule_type='care_system',
            location=final_location_name
        )
        
        db.session.add(dummy_schedule)
        db.session.commit()
        
        print(f"✅ 돌봄시스템 빈 장소 생성 완료: {final_location_name}")
        
        return jsonify({
            'success': True, 
            'message': f'"{location_name}" 장소가 생성되었습니다.',
            'location_name': location_name,
            'day_of_week': day_of_week,
            'care_type': care_type,
            'session_part': session_part,
            'dummy_created': True
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 돌봄시스템 빈 장소 생성 실패: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})