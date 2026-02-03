import sqlite3

DB_PATH = r"instance/app.db"  # ✅ instance DB를 바라봄

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 테이블 목록 확인
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
print("현재 DB 테이블 목록:", tables)

# contact 테이블 자동 찾기 (contact / contacts 등)
cands = [t for t in tables if "contact" in t.lower()]
if not cands:
    print("❌ contact 관련 테이블을 못 찾았습니다. 위 테이블 목록을 확인하세요.")
    conn.close()
    raise SystemExit(1)

table = cands[0]
print("✅ 대상 테이블:", table)

# 컬럼 확인
cur.execute(f"PRAGMA table_info({table});")
cols = [row[1] for row in cur.fetchall()]
print("현재 컬럼:", cols)

# status 컬럼 추가
if "status" not in cols:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN status TEXT DEFAULT '대기';")
    conn.commit()
    print("✅ status 컬럼 추가 완료")
else:
    print("✅ status 컬럼이 이미 존재합니다")

# 기존 데이터 NULL 채우기
cur.execute(f"UPDATE {table} SET status='대기' WHERE status IS NULL;")
conn.commit()
print("✅ 기존 데이터 status NULL → '대기'로 채움")

conn.close()
print("🎉 마이그레이션 완료!")