with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"525번째 줄: {lines[524].strip()}")

# location|tojson을 안전한 형태로 변경
old_line = lines[524]
new_line = old_line.replace('{{ location|tojson }}', "'{{ location }}'")

lines[524] = new_line

with open('templates/schedule.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"수정된 줄: {new_line.strip()}")
print("✅ location|tojson 수정 완료!") 