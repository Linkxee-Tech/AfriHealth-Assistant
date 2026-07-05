import sqlite3
from pathlib import Path

# Determine DB path from .env DB_PATH or fallback to frontend/afrihealth.db
env_path = Path(__file__).resolve().parent.parent / '.env'
db_path_from_env = None
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith('DB_PATH='):
            db_path_from_env = line.split('=', 1)[1].strip()
            break

if db_path_from_env:
    DB_PATH = Path(db_path_from_env)
else:
    DB_PATH = Path(__file__).resolve().parent.parent / 'frontend' / 'afrihealth.db'

if not DB_PATH.exists():
    print('DB not found at', DB_PATH)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
patterns = [
    '%You exceeded your current quota%','%insufficient_quota%','%Cloud AI Fallback failed%','%OPENAI%','%openai%'
]
new_content = '(Previous cloud fallback error message sanitized. Local LLM used.)'

total = 0
for p in patterns:
    cur.execute('SELECT COUNT(*) FROM messages WHERE content LIKE ?', (p,))
    c = cur.fetchone()[0]
    if c:
        print(f'Found {c} messages matching {p}, sanitizing...')
        cur.execute('UPDATE messages SET content = ? WHERE content LIKE ?', (new_content, p))
        total += c

conn.commit()
conn.close()
print('Sanitization complete. Total messages updated:', total)
