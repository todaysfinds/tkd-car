#!/usr/bin/env python3

import re

with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"수정 전 onclick 개수: {content.count('onclick=')}")

# 🎯 가장 위험한 패턴들만 수정 (location|tojson 포함)
dangerous_patterns = [
    # 학생 추가 (location|tojson 포함)
    (r'onclick="addStudentToLocation\((\{\{ day_num \}\}), (\d+), (\{\{ location\|tojson \}\}), \'([^\']+)\'\)"',
     r'data-day="\1" data-session="\2" data-location="{{ location }}" data-type="\4" class="add-regular-student-btn" onclick="addStudentToLocation(\1, \2, \'{{ location }}\', \'\4\')"'),
    
    # 돌봄시스템 학생 추가
    (r'onclick="addStudentToCareSystem\((\{\{ day_num \}\}), (\{\{ location\|tojson \}\}), \'([^\']+)\'\)"',
     r'data-day="\1" data-location="{{ location }}" data-care-type="\3" class="add-care-student-btn" onclick="addStudentToCareSystem(\1, \'{{ location }}\', \'\3\')"'),
    
    # 국가대표 훈련 학생 추가
    (r'onclick="addStudentToNationalTraining\((\{\{ day_num \}\}), (\{\{ location\|tojson \}\})\)"',
     r'data-day="\1" data-location="{{ location }}" class="add-national-student-btn" onclick="addStudentToNationalTraining(\1, \'{{ location }}\')"'),
    
    # 장소 설정 (가장 위험한 패턴)
    (r'onclick="showLocationSettings\((\{\{ day_num \}\}), (\{\{ location\|tojson \}\}), \'([^\']+)\', ?([^)]*)\)"',
     r'data-day="\1" data-location="{{ location }}" data-location-type="\3" data-session="\4" class="location-settings-btn" onclick="showLocationSettings(\1, \'{{ location }}\', \'\3\', \4)"'),
    
    # 학생 제거 (location|tojson 포함)
    (r'onclick="removeStudentFromLocation\((\{\{ student_data\.student\.id \}\}), (\{\{ day_num \}\}), (\{\{ location\|tojson \}\}), (\d+), \'([^\']+)\'\)"',
     r'data-student-id="\1" data-day="\2" data-location="{{ location }}" data-session="\4" data-type="\5" class="remove-student-btn" onclick="removeStudentFromLocation(\1, \2, \'{{ location }}\', \4, \'\5\')"'),
    
    # 돌봄시스템 학생 제거
    (r'onclick="removeStudentFromCareSystem\((\{\{ student_data\.student\.id \}\}), (\{\{ day_num \}\}), (\{\{ location\|tojson \}\}), \'([^\']+)\'\)"',
     r'data-student-id="\1" data-day="\2" data-location="{{ location }}" data-care-type="\4" class="remove-care-student-btn" onclick="removeStudentFromCareSystem(\1, \2, \'{{ location }}\', \'\4\')"'),
    
    # 국가대표 훈련 학생 제거
    (r'onclick="removeStudentFromNationalTraining\((\{\{ student_data\.student\.id \}\}), (\{\{ day_num \}\}), (\{\{ location\|tojson \}\})\)"',
     r'data-student-id="\1" data-day="\2" data-location="{{ location }}" class="remove-national-student-btn" onclick="removeStudentFromNationalTraining(\1, \2, \'{{ location }}\')"'),
]

# 위험한 패턴들 수정
for pattern, replacement in dangerous_patterns:
    before_count = len(re.findall(pattern, content))
    content = re.sub(pattern, replacement, content)
    if before_count > 0:
        print(f"✅ 수정: {before_count}개 - location|tojson 패턴")

print(f"수정 후 onclick 개수: {content.count('onclick=')}")
print(f"location|tojson 개수: {content.count('location|tojson')}")

with open('templates/schedule.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 최소한의 안전 수정 완료!")
print("   - location|tojson이 포함된 위험한 onclick만 수정")
print("   - 나머지 onclick은 그대로 유지")
print("   - 기존 기능 모두 보존") 