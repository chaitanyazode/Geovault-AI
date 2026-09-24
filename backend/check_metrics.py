from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
print('=== production_annual ===')
res = db.execute(text('SELECT mine_code, year, actual_production_mt, target_mt, achievement_pct, variance_mt FROM production_annual ORDER BY mine_code, year')).fetchall()
for r in res:
    print(r)

print('\n=== searching document_chunks ===')
res2 = db.execute(text("SELECT chunk_id, document_id, chunk_text FROM document_chunks WHERE chunk_text ILIKE '%56,100%' OR chunk_text ILIKE '%56100%' OR chunk_text ILIKE '%56.1%' OR chunk_text ILIKE '%5.02%'")).fetchall()
for r in res2:
    print(r[0], r[1], repr(r[2][:200]))

print('\n=== checking any mentions of GEVRA production in document_chunks ===')
res3 = db.execute(text("SELECT chunk_id, document_id, chunk_text FROM document_chunks WHERE chunk_text ILIKE '%GEVRA%' AND chunk_text ILIKE '%production%'")).fetchall()
for r in res3:
    print(r[0], r[1], repr(r[2][:200]))
