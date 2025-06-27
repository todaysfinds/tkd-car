#!/usr/bin/env python3

import re

with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

# JavaScript에서 찾는 class 이름들
expected_classes = [
    'day-nav-btn',
    'add-regular-student-btn', 
    'add-care-student-btn',
    'add-national-student-btn',
    'remove-student-btn',
    'remove-care-student-btn', 
    'remove-national-student-btn',
    'location-settings-btn',
    'add-new-location-btn',
    'admin-cleanup-btn',
    'student-attendance-btn',
    'modal-close-btn',
    'confirm-add-students-btn',
    'save-location-settings-btn',
    'delete-location-btn',
    'location-settings-close-btn'
]

print("HTML에서 찾은 class들:")
for class_name in expected_classes:
    count = content.count(f'class="{class_name}"') + content.count(f'class="') 
    if class_name in content:
        matches = len(re.findall(rf'class="[^"]*\b{class_name}\b[^"]*"', content))
        print(f"✅ {class_name}: {matches}개")
    else:
        print(f"❌ {class_name}: 없음")
        
print(f"\n전체 onclick 개수: {content.count('onclick=')}")
print(f"data- 속성 개수: {content.count('data-')}") 