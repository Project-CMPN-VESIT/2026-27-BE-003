import psycopg

def main():
    conn = psycopg.connect(dbname='tenant_db', user='postgres', password='rasika23', host='localhost')
    cur = conn.cursor()
    cur.execute("UPDATE audit_runs SET hash_version = 'v2' WHERE hash_version = 'legacy' OR hash_version = 'v1'")
    conn.commit()
    print("Updated hash_version in audit_runs to v2")
    conn.close()

if __name__ == '__main__':
    main()
