#!/usr/bin/env python3
import re

# 파일 읽기
with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 모든 {{ location|tojson }} 패턴을 '{{ location }}'으로 교체
fixed_content = re.sub(r'\{\{\s*location\|tojson\s*\}\}', "'{{ location }}'", content)

# 파일 저장
with open('templates/schedule.html', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("✅ 모든 location|tojson 패턴이 교체되었습니다!")

# 남은 패턴 개수 확인
remaining = len(re.findall(r'\{\{\s*location\|tojson\s*\}\}', fixed_content))
print(f"남은 location|tojson 패턴: {remaining}개") 