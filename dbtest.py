import psycopg2

db_url = ""

conn = psycopg2.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT 1;")
print("DB OK:", cur.fetchone())
cur.close()
conn.close()
