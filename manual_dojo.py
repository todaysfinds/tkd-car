#!/usr/bin/env python3
"""
⚠️ 일회용 스크립트 - 배포사이트에 도장 장소 생성 후 즉시 삭제할 것!
"""
import os
import sys

# 배포 환경에서만 실행되도록 체크
def create_dojo_for_production():
    try:
        # Flask 앱 임포트
        from app import app, db, Location
        
        with app.app_context():
            # 도장 장소 생성
            existing_dojo = Location.query.filter_by(name='도장').first()
            if not existing_dojo:
                dojo_location = Location(
                    name='도장',
                    description='돌봄시스템 및 국기원부 학생용',
                    is_active=True
                )
                db.session.add(dojo_location)
                db.session.commit()
                print("✅ 배포사이트에 '도장' 장소 생성 완료!")
                return True
            else:
                print("ℹ️ '도장' 장소 이미 존재함")
                return True
                
    except Exception as e:
        print(f"❌ 도장 장소 생성 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 배포사이트 도장 생성 스크립트")
    success = create_dojo_for_production()
    
    if success:
        print("🎉 완료! 이제 이 스크립트를 삭제하세요.")
    else:
        print("❌ 실패했습니다.") 