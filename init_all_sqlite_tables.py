import re
import sqlite3
from pathlib import Path

db_path = Path(r"C:\Users\DS\.gemini\antigravity\scratch\zhinianboke-xianyu-auto-reply\data\xianyu_data.db")
init_db_py = Path(r"C:\Users\DS\.gemini\antigravity\scratch\zhinianboke-xianyu-auto-reply\common\db\init_database.py").read_text(encoding="utf-8")

table_blocks = re.findall(r"(CREATE TABLE IF NOT EXISTS [\s\S]+?;)", init_db_py, re.I)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

for ddl in table_blocks:
    # Clean up MySQL specific syntax
    clean_ddl = re.sub(r"\)\s*ENGINE=[\s\S]*?;", ");", ddl, flags=re.I)
    clean_ddl = re.sub(r"COMMENT\s+(['\"]).*?\1", "", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bON\s+UPDATE\s+CURRENT_TIMESTAMP\b", "", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bLONGTEXT\b", "TEXT", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bJSON\b", "TEXT", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bBIGINT\b\s+AUTO_INCREMENT", "INTEGER PRIMARY KEY AUTOINCREMENT", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bINT\b\s+AUTO_INCREMENT", "INTEGER PRIMARY KEY AUTOINCREMENT", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bAUTO_INCREMENT\b", "", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bTINYINT\(\d+\)", "INTEGER", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bBIGINT\(\d+\)", "INTEGER", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bINT\(\d+\)", "INTEGER", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"\bDATETIME\(\d+\)", "DATETIME", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"CHARACTER SET \w+", "", clean_ddl, flags=re.I)
    clean_ddl = re.sub(r"COLLATE \w+", "", clean_ddl, flags=re.I)

    lines = clean_ddl.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(KEY|UNIQUE KEY|FULLTEXT KEY|INDEX)\s+[`\w]+\s*\(", stripped, re.I):
            continue
        filtered_lines.append(line)
    
    clean_ddl = "\n".join(filtered_lines)
    clean_ddl = re.sub(r",\s*\)", "\n)", clean_ddl)

    try:
        cursor.execute(clean_ddl)
    except Exception as e:
        print(f"Error executing DDL: {e}\nSQL:\n{clean_ddl[:300]}")

conn.commit()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"\nTOTAL SQLite Tables created successfully: {len(tables)}")
print("Tables:", sorted([t[0] for t in tables]))
conn.close()
