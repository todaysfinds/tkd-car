#!/usr/bin/env python3

with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 마지막 남은 onclick 수정
old_pattern = 'onclick="showLocationSettings({{ day_num }}, {{ location|tojson }}, \'national_training\')"'
new_pattern = 'class="location-settings-btn" data-day="{{ day_num }}" data-location="{{ location }}" data-location-type="national_training"'

content = content.replace(old_pattern, new_pattern)

with open('templates/schedule.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 마지막 onclick 이벤트 수정 완료!")

# 확인
onclick_count = content.count('onclick=')
print(f"남은 onclick 개수: {onclick_count}") 