#!/usr/bin/env python3
"""
모든 onclick 이벤트를 완전히 제거하고 data 속성으로 변환
"""

import re

def fix_all_onclick_events():
    with open('templates/schedule.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 관리자 도구 버튼들 수정
    content = re.sub(
        r'<button onclick="cleanupAllDuplicates\(\)"([^>]*)>',
        r'<button class="admin-cleanup-btn" data-action="cleanup-all"\1>',
        content
    )
    
    content = re.sub(
        r'<button onclick="showDuplicateCleanupModal\(\)"([^>]*)>',
        r'<button class="admin-cleanup-btn" data-action="cleanup-specific"\1>',
        content
    )
    
    # 2. 돌봄시스템 학생 추가 버튼 (care1, care2, care3)
    content = re.sub(
        r'onclick="addStudentToCareSystem\(\{\{ day_num \}\}, \{\{ location\|tojson \}\}, \'(care[123])\'\)"',
        r'class="add-care-student-btn" data-day="{{ day_num }}" data-location="{{ location }}" data-care-type="\1"',
        content
    )
    
    # 3. 일반 세션 학생 추가 버튼 (1-5부)
    content = re.sub(
        r'onclick="addStudentToLocation\(\{\{ day_num \}\}, (\d+), \{\{ location\|tojson \}\}, \'(pickup|dropoff)\'\)"',
        r'class="add-regular-student-btn" data-day="{{ day_num }}" data-session="\1" data-location="{{ location }}" data-type="\2"',
        content
    )
    
    # 4. 국가대표 학생 추가 버튼
    content = re.sub(
        r'onclick="addStudentToNationalTraining\(\{\{ day_num \}\}, \{\{ location\|tojson \}\}\)"',
        r'class="add-national-student-btn" data-day="{{ day_num }}" data-location="{{ location }}"',
        content
    )
    
    # 5. 장소 설정 버튼들
    content = re.sub(
        r'onclick="showLocationSettings\(\{\{ day_num \}\}, \{\{ location\|tojson \}\}, \'(pickup|dropoff|care_system|national_training)\', ?(\d+|\'care[123]\')\)"',
        r'class="location-settings-btn" data-day="{{ day_num }}" data-location="{{ location }}" data-location-type="\1" data-session-part="\2"',
        content
    )
    
    # 6. 학생 제거 버튼들 (일반)
    content = re.sub(
        r'onclick="removeStudentFromLocation\(\{\{ student_data\.student\.id \}\}, \{\{ day_num \}\}, \{\{ location\|tojson \}\}, (\d+), \'(pickup|dropoff)\'\)"',
        r'class="remove-student-btn" data-student-id="{{ student_data.student.id }}" data-day="{{ day_num }}" data-location="{{ location }}" data-session="\1" data-type="\2"',
        content
    )
    
    # 7. 학생 제거 버튼들 (돌봄시스템)
    content = re.sub(
        r'onclick="removeStudentFromCareSystem\(\{\{ student_data\.student\.id \}\}, \{\{ day_num \}\}, \{\{ location\|tojson \}\}, \'(care[123])\'\)"',
        r'class="remove-care-student-btn" data-student-id="{{ student_data.student.id }}" data-day="{{ day_num }}" data-location="{{ location }}" data-care-type="\1"',
        content
    )
    
    # 8. 학생 제거 버튼들 (국가대표)
    content = re.sub(
        r'onclick="removeStudentFromNationalTraining\(\{\{ student_data\.student\.id \}\}, \{\{ day_num \}\}, \{\{ location\|tojson \}\}\)"',
        r'class="remove-national-student-btn" data-student-id="{{ student_data.student.id }}" data-day="{{ day_num }}" data-location="{{ location }}"',
        content
    )
    
    # 9. 새 장소 추가 버튼들 (일반)
    content = re.sub(
        r'onclick="addNewLocation\(\{\{ day_num \}\}, (\d+), \'(pickup|dropoff)\'\)"',
        r'class="add-new-location-btn" data-day="{{ day_num }}" data-session="\1" data-type="\2"',
        content
    )
    
    # 10. 새 장소 추가 버튼들 (돌봄시스템)
    content = re.sub(
        r'onclick="addNewLocationToCareSystem\(\{\{ day_num \}\}, \'(care[123])\'\)"',
        r'class="add-new-location-btn" data-day="{{ day_num }}" data-care-type="\1"',
        content
    )
    
    # 11. 새 장소 추가 버튼들 (국가대표)
    content = re.sub(
        r'onclick="addNewLocationToNationalTraining\(\{\{ day_num \}\}, \'national\'\)"',
        r'class="add-new-location-btn" data-day="{{ day_num }}" data-location-type="national"',
        content
    )
    
    # 12. 학생 출석 토글 버튼
    content = re.sub(
        r'onclick="toggleStudentAttendance\(\{\{ student_data\.student\.id \}\}\)"',
        r'class="student-attendance-btn" data-student-id="{{ student_data.student.id }}"',
        content
    )
    
    # 13. 모달 관련 버튼들
    content = re.sub(
        r'onclick="closeModal\(\)"',
        r'class="modal-close-btn"',
        content
    )
    
    content = re.sub(
        r'onclick="confirmAddStudents\(\)"',
        r'class="confirm-add-students-btn"',
        content
    )
    
    content = re.sub(
        r'onclick="deleteLocation\(\)"',
        r'class="delete-location-btn"',
        content
    )
    
    content = re.sub(
        r'onclick="closeLocationSettings\(\)"',
        r'class="location-settings-close-btn"',
        content
    )
    
    content = re.sub(
        r'onclick="saveLocationSettings\(\)"',
        r'class="save-location-settings-btn"',
        content
    )
    
    # 백업 생성
    with open('templates/schedule_before_fix.html', 'w', encoding='utf-8') as f:
        f.write(open('templates/schedule.html', 'r', encoding='utf-8').read())
    
    # 수정된 내용 저장
    with open('templates/schedule.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 모든 onclick 이벤트 제거 완료!")
    print("📁 백업 파일: templates/schedule_before_fix.html")

if __name__ == "__main__":
    fix_all_onclick_events() 