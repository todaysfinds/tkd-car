#!/usr/bin/env python3

with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"전체 줄 수: {len(lines)}")
if len(lines) >= 525:
    print(f"525번째 줄: {lines[524].strip()}")
    print(f"524번째 줄: {lines[523].strip()}")
    print(f"526번째 줄: {lines[525].strip()}")
    
    # 주변 몇 줄도 확인
    for i in range(520, 530):
        if i < len(lines):
            marker = ">>> " if i == 524 else "    "
            print(f"{marker}{i+1}: {lines[i].strip()[:100]}") 