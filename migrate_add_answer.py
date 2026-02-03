import sqlite3

DB_PATH = "instance/app.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
print("테이블:", tables)

table = "contact" if "contact" in tables else ("contacts" if "contacts" in tables else None)
if not table:
    raise RuntimeError("contact 테이블을 찾지 못했습니다.")

print("대상 테이블:", table)

cur.execute(f"PRAGMA table_info({table});")
cols = [row[1] for row in cur.fetchall()]
print("현재 컬럼:", cols)

if "answer" not in cols:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN answer TEXT DEFAULT '';")
    print("✅ answer 컬럼 추가")

if "answered_at" not in cols:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN answered_at DATETIME;")
    print("✅ answered_at 컬럼 추가")

conn.commit()
conn.close()
print("🎉 마이그레이션 완료")