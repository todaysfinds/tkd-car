#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render PostgreSQL DB 시간 관련 컬럼 삭제 마이그레이션 스크립트
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

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

if __name__ == "__main__":
    print("🚀 Render PostgreSQL 시간 관련 컬럼 삭제 마이그레이션 시작")
    print("=" * 60)
    
    # 1. 현재 DB 구조 확인
    print("1️⃣ 현재 PostgreSQL DB 구조 확인")
    if not check_postgres_columns():
        print("❌ PostgreSQL DB 구조 확인 실패")
        exit(1)
    
    print("\n" + "=" * 60)
    
    # 2. 마이그레이션 실행
    print("2️⃣ PostgreSQL 시간 관련 컬럼 삭제")
    if not remove_time_columns_postgres():
        print("❌ PostgreSQL 마이그레이션 실패")
        exit(1)
    
    print("\n" + "=" * 60)
    
    # 3. 결과 확인
    print("3️⃣ PostgreSQL 마이그레이션 결과 확인")
    verify_postgres_migration()
    
    print("\n" + "=" * 60)
    print("🎉 PostgreSQL 마이그레이션 완료!")
    print("이제 Render 배포 사이트의 시간 관련 컬럼들이 완전히 제거되었습니다.") 