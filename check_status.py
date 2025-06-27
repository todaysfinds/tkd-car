with open('templates/schedule.html', 'r', encoding='utf-8') as f:
    content = f.read()

onclick_count = content.count('onclick=')
tojson_count = content.count('location|tojson')

print(f"onclick 개수: {onclick_count}")
print(f"location|tojson 개수: {tojson_count}")

if tojson_count > 0:
    print("⚠️ 아직 위험한 location|tojson 패턴이 남아있습니다!")
else:
    print("✅ location|tojson 패턴이 모두 제거되었습니다!") 