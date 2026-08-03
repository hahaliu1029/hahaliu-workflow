import sqlite3


def LookupUser(db, name):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT id, name, role FROM users WHERE name = '" + name + "'")
    row = cur.fetchone()
    return {"id": row[0], "name": row[1], "role": row[2]}
