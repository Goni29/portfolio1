import sqlite3

DB_PATH = "instance/app.db"   # ✅ 반드시 instance DB

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 테이블/컬럼 확인
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
print("테이블:", tables)

# contact 테이블 찾기
if "contact" in tables:
    table = "contact"
elif "contacts" in tables:
    table = "contacts"
else:
    # 혹시 contact 포함된 이름이 있으면 그걸 사용
    cands = [t for t in tables if "contact" in t.lower()]
    if not cands:
        raise RuntimeError("contact 테이블을 찾지 못했습니다.")
    table = cands[0]

print("대상 테이블:", table)

cur.execute(f"PRAGMA table_info({table});")
cols = [row[1] for row in cur.fetchall()]
print("컬럼:", cols)

# 컬럼 추가
if "password_hash" not in cols:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN password_hash TEXT;")
    conn.commit()
    print("✅ password_hash 컬럼 추가 완료")
else:
    print("✅ 이미 password_hash 컬럼이 존재합니다")

conn.close()
print("🎉 마이그레이션 완료")