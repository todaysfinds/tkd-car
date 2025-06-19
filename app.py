from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tkd_transport.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 데이터베이스 모델
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    pickup_location = db.Column(db.String(100))
    estimated_pickup_time = db.Column(db.String(10))  # 예상 픽업 시간 (12시간제)
    is_private_car = db.Column(db.Boolean, default=False)  # 개인차량 여부
    memo = db.Column(db.String(200))  # 메모 필드 추가
    session_part = db.Column(db.Integer)  # 부 (1부, 2부, 3부, 4부, 5부)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=월요일, 6=일요일
    pickup_time = db.Column(db.Time, nullable=False)
    dropoff_time = db.Column(db.Time, nullable=False)
    
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

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    pickup_time = db.Column(db.Time)
    dropoff_time = db.Column(db.Time)
    pickup_status = db.Column(db.String(20), default='pending')  # 'pending', 'boarded', 'absent', 'parent_pickup'
    dropoff_status = db.Column(db.String(20), default='pending')  # 'pending', 'dropped', 'absent', 'dojo_pickup'
    notes = db.Column(db.Text)
    
    student = db.relationship('Student', backref=db.backref('attendances', lazy=True))

# 라우트
@app.route('/')
def index():
    return redirect(url_for('today'))

@app.route('/today')
def today():
    today_date = date.today()
    day_of_week = today_date.weekday()
    
    # 오늘 스케줄이 있는 학생들 조회 (시간 순서대로 정렬)
    students_with_schedule = db.session.query(Student, Schedule).join(Schedule).filter(
        Schedule.day_of_week == day_of_week
    ).order_by(Schedule.pickup_time, Student.pickup_location, Student.estimated_pickup_time).all()
    
    # 시간 순서대로 그룹화 (승차/하차 구분)
    time_groups = {}
    
    for student, schedule in students_with_schedule:
        # 시간 키 생성 (24시간제 → 12시간제 변환)
        pickup_hour = schedule.pickup_time.hour
        pickup_minute = schedule.pickup_time.minute
        
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
        location_key = student.pickup_location or '미정'
        if location_key not in time_groups[time_key]:
            time_groups[time_key][location_key] = []
        
        # 오늘 출석 정보 조회
        attendance = Attendance.query.filter_by(
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
    # 요일별, 부별, 장소별로 그룹화된 데이터 구조 생성
    schedule_data = {}
    
    # 모든 스케줄 조회
    schedules = db.session.query(Student, Schedule).join(Schedule).order_by(
        Schedule.day_of_week, Schedule.pickup_time, Student.pickup_location, Student.name
    ).all()
    
    for student, schedule in schedules:
        day = schedule.day_of_week
        part = student.session_part or 1
        location = student.pickup_location or '미정'
        
        # 요일별 구조 초기화
        if day not in schedule_data:
            schedule_data[day] = {}
        
        # 부별 구조 초기화
        if part not in schedule_data[day]:
            schedule_data[day][part] = {}
            
        # 장소별 구조 초기화
        if location not in schedule_data[day][part]:
            schedule_data[day][part][location] = []
            
        # 학생 추가
        schedule_data[day][part][location].append({
            'student': student,
            'schedule': schedule
        })
    
    return render_template('admin_schedule_manager.html', schedule_data=schedule_data)

@app.route('/admin/students')
def admin_students():
    students = Student.query.order_by(Student.name).all()
    return render_template('admin_students.html', students=students)

@app.route('/api/update_attendance', methods=['POST'])
def update_attendance():
    data = request.get_json()
    student_id = data.get('student_id')
    attendance_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    status = data.get('status')
    attendance_type = data.get('type', 'pickup')  # pickup or dropoff
    
    attendance = Attendance.query.filter_by(
        student_id=student_id,
        date=attendance_date
    ).first()
    
    if not attendance:
        attendance = Attendance(student_id=student_id, date=attendance_date)
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
        data = request.get_json()
        name = data.get('name')
        default_time = data.get('default_time')
        
        if not name:
            return jsonify({'success': False, 'message': '장소명이 필요합니다.'})
        
        # 중복 체크
        existing_students = Student.query.filter_by(pickup_location=name).first()
        if existing_students:
            return jsonify({'success': False, 'message': '이미 존재하는 장소입니다.'})
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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
        # 현재 사용 중인 모든 장소 목록 반환
        locations = db.session.query(Student.pickup_location).filter(
            Student.pickup_location.isnot(None)
        ).distinct().all()
        
        location_list = [loc[0] for loc in locations if loc[0]]
        return jsonify({'success': True, 'locations': location_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 학생 관리 API
@app.route('/api/add_student', methods=['POST'])
def add_student():
    try:
        name = request.form.get('name')
        birth_year = request.form.get('birth_year')
        
        if not name:
            return jsonify({'success': False, 'error': '이름을 입력해주세요.'})
        
        # 새 학생 추가 (간단한 정보만)
        new_student = Student(
            name=name,
            grade=birth_year  # grade 필드를 출생년도로 사용
        )
        
        db.session.add(new_student)
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check_duplicate_name', methods=['POST'])
def check_duplicate_name():
    try:
        data = request.get_json()
        name = data.get('name')
        exclude_id = data.get('exclude_id')
        
        query = Student.query.filter_by(name=name)
        if exclude_id:
            query = query.filter(Student.id != exclude_id)
        
        existing_student = query.first()
        
        return jsonify({
            'success': True,
            'duplicate': existing_student is not None
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_student', methods=['POST'])
def update_student():
    try:
        data = request.get_json()
        student_id = data.get('id')
        name = data.get('name')
        birth_year = data.get('birth_year')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        student.name = name
        student.grade = birth_year
        
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_student', methods=['POST'])
def delete_student():
    try:
        data = request.get_json()
        student_id = data.get('id')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        # 관련된 스케줄, 요청, 출석 정보도 함께 삭제
        Schedule.query.filter_by(student_id=student_id).delete()
        Request.query.filter_by(student_id=student_id).delete()
        Attendance.query.filter_by(student_id=student_id).delete()
        
        db.session.delete(student)
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        day_of_week = data.get('day_of_week')
        session_part = data.get('session_part')
        schedule_type = data.get('type')  # 'pickup' or 'dropoff'
        target_location = data.get('location')  # 장소 정보
        
        # 학생 정보 확인
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'error': '학생을 찾을 수 없습니다.'})
        
        # 중복 허용 - 같은 학생이 같은 날 여러 장소에 올 수 있음
        # 기존 중복 체크 제거
        
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
        else:  # 5부
            pickup_time = time(19, 0)  # 7:00 PM
            dropoff_time = time(19, 50)  # 7:50 PM
        
        # 학생의 부 정보 및 장소 정보 업데이트
        student.session_part = session_part
        if target_location:
            student.pickup_location = target_location
        
        # 새 스케줄 추가
        new_schedule = Schedule(
            student_id=student_id,
            day_of_week=day_of_week,
            pickup_time=pickup_time,
            dropoff_time=dropoff_time
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        return jsonify({'success': True})
    
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
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        day_of_week = data.get('day_of_week')
        location = data.get('location')  # 특정 장소에서만 삭제
        session_part = data.get('session_part')  # 특정 시간대
        schedule_type = data.get('type', 'pickup')  # pickup 또는 dropoff
        
        # 특정 조건의 스케줄만 삭제 (개별 삭제)
        query = Schedule.query.filter_by(
            student_id=student_id,
            day_of_week=day_of_week
        )
        
        # 추가 조건들이 있으면 필터링
        if location:
            # student의 pickup_location이 해당 location과 일치하는 것만
            query = query.join(Student).filter(Student.pickup_location == location)
        if session_part:
            query = query.join(Student).filter(Student.session_part == session_part)
        
        schedule = query.first()
        
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '해당 스케줄을 찾을 수 없습니다.'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# 앱 초기화 함수
def init_db():
    import os
    with app.app_context():
        # 배포환경에서는 데이터 보존, 개발환경에서만 재생성
        if os.environ.get('RENDER') or os.environ.get('DATABASE_URL'):  # Render 환경 감지
            db.create_all()  # 테이블이 없으면 생성만
        else:
            db.drop_all()
            db.create_all()
        
        # 샘플 데이터 추가 (처음 실행시에만)
        try:
            if Student.query.count() == 0:
                # 실제 시간표 기반 샘플 학생 데이터
                students_data = [
                    # 1부 (2:00~2:50)
                    {'name': '홍길동', 'grade': '초등 3학년', 'phone': '010-1234-5678', 'pickup_location': '동부시스템', 'estimated_pickup_time': '2:40', 'session_part': 1, 'memo': ''},
                    {'name': '김철수', 'grade': '초등 4학년', 'phone': '010-2345-6789', 'pickup_location': '승차', 'estimated_pickup_time': '2:30', 'session_part': 1, 'memo': ''},
                    
                    # 2부 (3:00~3:50)  
                    {'name': '이영희', 'grade': '초등 2학년', 'phone': '010-1111-2222', 'pickup_location': '현대홈타운', 'estimated_pickup_time': '3:30', 'session_part': 2, 'memo': ''},
                    {'name': '박민수', 'grade': '초등 5학년', 'phone': '010-3333-4444', 'pickup_location': '삼성래미안', 'estimated_pickup_time': '3:40', 'session_part': 2, 'memo': ''},
                    {'name': '최수진', 'grade': '초등 3학년', 'phone': '010-4444-5555', 'pickup_location': '삼성래미안', 'estimated_pickup_time': '3:42', 'session_part': 2, 'memo': ''},
                    
                    # 3부 (4:30~5:20)
                    {'name': '정우성', 'grade': '초등 1학년', 'phone': '010-5555-6666', 'pickup_location': '현대홈타운', 'estimated_pickup_time': '4:15', 'session_part': 3, 'memo': ''},
                    {'name': '강호동', 'grade': '초등 4학년', 'phone': '010-6666-7777', 'pickup_location': '이화빌라', 'estimated_pickup_time': '4:10', 'session_part': 3, 'memo': ''},
                    {'name': '유재석', 'grade': '초등 6학년', 'phone': '010-7777-8888', 'pickup_location': '영은유치원', 'estimated_pickup_time': '4:14', 'session_part': 3, 'memo': ''},
                    
                    # 4부 (5:30~6:20)
                    {'name': '송중기', 'grade': '초등 2학년', 'phone': '010-8888-9999', 'pickup_location': '현대홈타운', 'estimated_pickup_time': '6:30', 'session_part': 4, 'memo': ''},
                    {'name': '전지현', 'grade': '초등 5학년', 'phone': '010-9999-0000', 'pickup_location': '이디야', 'estimated_pickup_time': '6:35', 'session_part': 4, 'memo': ''},
                    
                    # 5부 (7:00~7:50)
                    {'name': '김수현', 'grade': '초등 3학년', 'phone': '010-0000-1111', 'pickup_location': '승차', 'estimated_pickup_time': '6:35', 'session_part': 5, 'memo': ''},
                    {'name': '아이유', 'grade': '초등 4학년', 'phone': '010-1111-2222', 'pickup_location': '삼성래미안', 'estimated_pickup_time': '6:40', 'session_part': 5, 'memo': ''},
                ]
                
                for student_data in students_data:
                    student = Student(**student_data)
                    db.session.add(student)
                
                db.session.commit()
                
                # 샘플 스케줄 데이터 (월요일, 수요일, 금요일)
                students = Student.query.all()
                for student in students:
                    for day in [0, 2, 4]:  # 월, 수, 금
                        # 부별 시간 설정
                        if student.session_part == 1:  # 1부
                            pickup_time_obj = time(14, 0)  # 2:00 PM
                            dropoff_time_obj = time(14, 50)  # 2:50 PM
                        elif student.session_part == 2:  # 2부
                            pickup_time_obj = time(15, 0)  # 3:00 PM
                            dropoff_time_obj = time(15, 50)  # 3:50 PM
                        elif student.session_part == 3:  # 3부
                            pickup_time_obj = time(16, 30)  # 4:30 PM
                            dropoff_time_obj = time(17, 20)  # 5:20 PM
                        elif student.session_part == 4:  # 4부
                            pickup_time_obj = time(17, 30)  # 5:30 PM
                            dropoff_time_obj = time(18, 20)  # 6:20 PM
                        else:  # 5부
                            pickup_time_obj = time(19, 0)  # 7:00 PM
                            dropoff_time_obj = time(19, 50)  # 7:50 PM
                        
                        schedule = Schedule(
                            student_id=student.id,
                            day_of_week=day,
                            pickup_time=pickup_time_obj,
                            dropoff_time=dropoff_time_obj
                        )
                        db.session.add(schedule)
                
                db.session.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")
            pass

# 개발 환경에서만 Flask 직접 실행
if __name__ == '__main__':
    import os
    # 개발 환경에서만 데이터베이스 초기화
    init_db()
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    debug = not (os.environ.get('RENDER') or os.environ.get('DATABASE_URL'))
    app.run(host=host, port=port, debug=debug)
else:
    # 프로덕션 환경 (gunicorn)에서는 초기화 실행
    init_db() 