#!/usr/bin/env python3

with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

onclick_count = content.count('onclick=')
print(f"onclick 개수: {onclick_count}")

lines = content.split('\n')
for i, line in enumerate(lines):
    if 'onclick=' in line:
        print(f"{i+1}: {line.strip()[:100]}") 