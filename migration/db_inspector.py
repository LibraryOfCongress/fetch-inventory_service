import psycopg2
import json

def get_schema(dbname):
    conn = psycopg2.connect(f"dbname={dbname} user=postgres password=postgres host=localhost port=5432")
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    schema = {}
    for table in tables:
        # Get columns
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table}'
        """)
        schema[table] = {
            "columns": {row[0]: {"type": row[1], "nullable": row[2], "default": row[3]} for row in cur.fetchall()}
        }
    
    cur.close()
    conn.close()
    return schema

if __name__ == "__main__":
    lc_schema = get_schema("lc_baseline_db")
    fetch2_schema = get_schema("fetch2_clean_db")
    
    with open("lc_schema.json", "w") as f:
        json.dump(lc_schema, f, indent=2)
    with open("fetch2_schema.json", "w") as f:
        json.dump(fetch2_schema, f, indent=2)
