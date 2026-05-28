import os
import pandas as pd
import psycopg2

# 1. Leer archivo bajado del SFTP
df = pd.read_csv("/tmp/archivo.csv")

# 2. Conectar a PostgreSQL
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    port=os.environ["DB_PORT"]
)

cursor = conn.cursor()

# 3. Insertar filas
for _, row in df.iterrows():
    cursor.execute(
        "INSERT INTO tu_tabla (col1, col2, col3) VALUES (%s, %s, %s)",
        (row["col1"], row["col2"], row["col3"])
    )

conn.commit()
cursor.close()
conn.close()

print(f"✅ {len(df)} filas insertadas correctamente")
