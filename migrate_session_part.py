#!/usr/bin/env python3
"""
Student 테이블에 session_part 컬럼 마이그레이션 스크립트
배포사이트 PostgreSQL 데이터베이스에 안전하게 컬럼을 추가합니다.
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
import re

def get_render_db_url():
    """Render 환경변수에서 데이터베이스 URL 가져오기"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return None
    
    # postgres:// -> postgresql:// 변환
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # URL 파싱 개선
    try:
        parsed = urlparse(database_url)
        
        # 포트가 없으면 기본 포트 추가
        if not parsed.port:
            if parsed.scheme == 'postgresql':
                database_url = database_url.replace('postgresql://', 'postgresql://', 1)
                if '@' in database_url and ':' not in database_url.split('@')[1].split('/')[0]:
                    # 호스트에 포트가 없으면 추가
                    host_part = database_url.split('@')[1]
                    if '/' in host_part:
                        host, path = host_part.split('/', 1)
                        database_url = database_url.replace(f'@{host}/', f'@{host}:5432/')
                    else:
                        database_url = database_url + ':5432'
        
        print(f"🔧 파싱된 URL: {parsed.scheme}://{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:]}")
        
    except Exception as e:
        print(f"⚠️ URL 파싱 경고: {e}")
    
    return database_url

def check_column_exists(conn, table_name, column_name):
    """컬럼이 이미 존재하는지 확인"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            """, (table_name, column_name))
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"❌ 컬럼 존재 여부 확인 실패: {e}")
        return False

def parse_database_url(url):
    # postgresql://username:password@host:port/database
    from urllib.parse import urlparse
    fake_url = url.replace('postgresql://', 'http://', 1)
    parsed = urlparse(fake_url)
    username = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/')
    print(f"[DEBUG] username={username}, password=(hidden), host={host}, port={port}, database={database}")
    return username, password, host, port, database

def add_session_part_column():
    """Student 테이블에 session_part 컬럼 추가"""
    database_url = get_render_db_url()
    if not database_url:
        print("❌ 데이터베이스 URL을 가져올 수 없습니다.")
        return False
    
    print(f"🔍 PostgreSQL DB 연결: {database_url[:50]}...")
    
    try:
        username, password, host, port, database = parse_database_url(database_url)
        print(f"[DEBUG] username={username}, password=(hidden), host={host}, port={port}, database={database}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✅ 데이터베이스 연결 성공!")
        
        # session_part 컬럼이 이미 존재하는지 확인
        if check_column_exists(conn, 'student', 'session_part'):
            print("✅ session_part 컬럼이 이미 존재합니다.")
            conn.close()
            return True
        
        print("🔄 session_part 컬럼 추가 중...")
        
        with conn.cursor() as cursor:
            # session_part 컬럼 추가 (기본값 1)
            cursor.execute("""
                ALTER TABLE student 
                ADD COLUMN session_part INTEGER DEFAULT 1
            """)
            
            # 기존 데이터의 session_part를 1로 설정
            cursor.execute("""
                UPDATE student 
                SET session_part = 1 
                WHERE session_part IS NULL
            """)
            
            # 컬럼을 NOT NULL로 설정 (기본값이 있으므로 안전)
            cursor.execute("""
                ALTER TABLE student 
                ALTER COLUMN session_part SET NOT NULL
            """)
            
            print("✅ session_part 컬럼 추가 완료!")
            
            # 변경사항 확인
            cursor.execute("SELECT COUNT(*) FROM student")
            student_count = cursor.fetchone()[0]
            print(f"📊 총 학생 수: {student_count}명")
            
            cursor.execute("SELECT COUNT(*) FROM student WHERE session_part = 1")
            default_count = cursor.fetchone()[0]
            print(f"📊 기본값(1부) 설정된 학생 수: {default_count}명")
        
        conn.close()
        print("✅ 마이그레이션 완료!")
        return True
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_migration():
    """마이그레이션 결과 검증"""
    database_url = get_render_db_url()
    if not database_url:
        print("❌ 데이터베이스 URL을 가져올 수 없습니다.")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        
        with conn.cursor() as cursor:
            # session_part 컬럼 존재 확인
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'student' AND column_name = 'session_part'
            """)
            result = cursor.fetchone()
            
            if result:
                column_name, data_type, is_nullable, column_default = result
                print(f"✅ session_part 컬럼 확인:")
                print(f"   - 컬럼명: {column_name}")
                print(f"   - 데이터 타입: {data_type}")
                print(f"   - NULL 허용: {is_nullable}")
                print(f"   - 기본값: {column_default}")
                
                # 샘플 데이터 확인
                cursor.execute("""
                    SELECT id, name, session_part 
                    FROM student 
                    ORDER BY id 
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                print(f"📋 샘플 데이터:")
                for student_id, name, session_part in samples:
                    print(f"   - ID {student_id}: {name} ({session_part}부)")
                
                return True
            else:
                print("❌ session_part 컬럼을 찾을 수 없습니다.")
                return False
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Student 테이블 session_part 컬럼 마이그레이션 시작...")
    print("=" * 60)
    
    # 마이그레이션 실행
    if add_session_part_column():
        print("\n🔍 마이그레이션 결과 검증 중...")
        if verify_migration():
            print("\n🎉 마이그레이션 성공!")
        else:
            print("\n⚠️ 마이그레이션은 완료되었지만 검증에 실패했습니다.")
    else:
        print("\n❌ 마이그레이션 실패!") 