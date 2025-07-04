#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render PostgreSQL DB 시간 관련 컬럼 삭제 마이그레이션 스크립트
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from app import db, app

# .env 파일 로드
load_dotenv()

def get_render_db_url():
    # 정확한 Render DB 주소를 하드코딩
    return "postgresql://euirim:1DBMpSNDFK1OKMDzeBjxY7kDdlWBpiTs@dpg-d0vusoggjchc73a63srg-a.oregon-postgres.render.com:5432/bookclub_mslp"

def check_postgres_columns():
    """PostgreSQL DB에서 현재 컬럼 구조 확인"""
    try:
        database_url = get_render_db_url()
        if not database_url:
            return False
        
        print(f"🔍 PostgreSQL DB 연결: {database_url[:50]}...")
        
        # PostgreSQL 연결
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 테이블 목록 조회
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"📋 발견된 테이블: {[table[0] for table in tables]}")
        
        # 각 테이블의 컬럼 구조 확인
        for table in tables:
            table_name = table[0]
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"\n📊 {table_name} 테이블 컬럼:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"   - {col[0]} ({col[1]}) {nullable}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL DB 구조 확인 중 오류: {str(e)}")
        return False

def remove_time_columns_postgres():
    """PostgreSQL에서 시간 관련 컬럼들 삭제"""
    try:
        database_url = get_render_db_url()
        if not database_url:
            return False
        
        print(f"🔧 PostgreSQL 마이그레이션 시작")
        
        # PostgreSQL 연결
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 삭제할 컬럼들 정의
        columns_to_remove = [
            ('student', 'estimated_pickup_time'),
            ('student', 'session_part'),
            ('schedule', 'time'),
            ('location', 'default_time'),
            ('tkd_attendance', 'pickup_time'),
            ('tkd_attendance', 'dropoff_time')
        ]
        
        # 각 컬럼 삭제 시도
        for table_name, column_name in columns_to_remove:
            try:
                # 컬럼 존재 여부 확인
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table_name}' 
                    AND column_name = '{column_name}';
                """)
                column_exists = cursor.fetchone() is not None
                
                if column_exists:
                    print(f"🗑️ {table_name}.{column_name} 컬럼 삭제 중...")
                    
                    # PostgreSQL에서는 ALTER TABLE DROP COLUMN 사용
                    drop_sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};"
                    cursor.execute(drop_sql)
                    
                    print(f"✅ {table_name}.{column_name} 컬럼 삭제 완료")
                else:
                    print(f"ℹ️ {table_name}.{column_name} 컬럼이 이미 존재하지 않음")
                    
            except Exception as e:
                print(f"⚠️ {table_name}.{column_name} 컬럼 삭제 중 오류: {str(e)}")
                continue
        
        conn.close()
        print("✅ PostgreSQL 마이그레이션 완료!")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL 마이그레이션 중 오류: {str(e)}")
        return False

def verify_postgres_migration():
    """PostgreSQL 마이그레이션 결과 확인"""
    print("\n🔍 PostgreSQL 마이그레이션 결과 확인:")
    return check_postgres_columns()

def safe_reset_database():
    """안전한 데이터베이스 리셋 (개발용)"""
    try:
        with app.app_context():
            print("🗑️ 모든 테이블 삭제 중...")
            db.drop_all()
            print("✅ 테이블 삭제 완료")
            
            print("🏗️ 새 테이블 생성 중...")
            db.create_all()
            print("✅ 테이블 생성 완료")
            
            return True
    except Exception as e:
        print(f"❌ 데이터베이스 리셋 실패: {e}")
        return False

def migrate_add_order_column():
    """ScheduleLocation 테이블에 order 컬럼을 안전하게 추가하는 마이그레이션"""
    try:
        with app.app_context():
            print("🔄 ScheduleLocation order 컬럼 마이그레이션 시작...")
            
            # 현재 DB 종류 확인
            db_type = "sqlite" if "sqlite" in str(db.engine.url).lower() else "postgresql"
            print(f"📊 데이터베이스 타입: {db_type}")
            
            # order 컬럼이 이미 존재하는지 확인
            try:
                result = db.session.execute(db.text("SELECT \"order\" FROM schedule_location LIMIT 1"))
                print("✅ order 컬럼이 이미 존재합니다.")
                return True
            except Exception:
                print("🔍 order 컬럼이 없음 - 추가 작업 진행")
            
            if db_type == "sqlite":
                # SQLite는 ALTER TABLE ADD COLUMN만 지원하므로 제약조건 없이 추가
                print("📝 SQLite: order 컬럼 추가...")
                db.session.execute(db.text('ALTER TABLE schedule_location ADD COLUMN "order" INTEGER DEFAULT 0'))
                
            else:
                # PostgreSQL: 컬럼 추가 후 제약조건 추가
                print("📝 PostgreSQL: order 컬럼과 제약조건 추가...")
                db.session.execute(db.text('ALTER TABLE schedule_location ADD COLUMN "order" INTEGER DEFAULT 0'))
                
                # NOT NULL 제약조건 추가
                db.session.execute(db.text('ALTER TABLE schedule_location ALTER COLUMN "order" SET NOT NULL'))
                
                # 고유 제약조건 추가 (SQLite에서는 런타임에 처리)
                try:
                    db.session.execute(db.text('''
                        ALTER TABLE schedule_location 
                        ADD CONSTRAINT uq_schedule_location_order 
                        UNIQUE (day_of_week, session_part, type, "order")
                    '''))
                except Exception as e:
                    print(f"⚠️ 제약조건 추가 실패 (이미 존재할 수 있음): {e}")
            
            db.session.commit()
            
            # 기존 데이터에 order 값 부여
            from app import migrate_schedule_location_order
            migrate_schedule_location_order()
            
            print("✅ order 컬럼 마이그레이션 완료!")
            return True
            
    except Exception as e:
        print(f"❌ order 컬럼 마이그레이션 실패: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    choice = input("선택하세요 - [1] 전체 리셋 [2] order 컬럼 마이그레이션: ")
    
    if choice == "1":
        if safe_reset_database():
            print("🎉 데이터베이스 리셋 완료!")
        else:
            print("💥 리셋 실패!")
    elif choice == "2":
        if migrate_add_order_column():
            print("🎉 order 컬럼 마이그레이션 완료!")
        else:
            print("💥 마이그레이션 실패!")
    else:
        print("❌ 잘못된 선택입니다.") 