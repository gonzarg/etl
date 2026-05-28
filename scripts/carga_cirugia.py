import os
import re
import paramiko
import pandas as pd
import psycopg2
from datetime import datetime

# ── Configuración ──────────────────────────────────────────
SFTP_HOST     = os.environ["SFTP_HOST"]
SFTP_USER     = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
SFTP_PATH     = os.environ["SFTP_PATH"]  # carpeta donde está el archivo

DB_HOST     = os.environ["DB_HOST"]
DB_NAME     = os.environ["DB_NAME"]
DB_USER     = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_PORT     = os.environ["DB_PORT"]

# ── Nombre del archivo con fecha de hoy ────────────────────
hoy = datetime.now().strftime("%Y.%m.%d")
nombre_archivo = f"{hoy}_Protocolos_quirurgicos.csv"
local_path = f"/tmp/{nombre_archivo}"

# ── 1. Bajar archivo desde SFTP ────────────────────────────
print(f"Descargando {nombre_archivo} desde SFTP...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SFTP_HOST, username=SFTP_USER, password=SFTP_PASSWORD)
sftp = ssh.open_sftp()
sftp.get(f"{SFTP_PATH}/{nombre_archivo}", local_path)
sftp.close()
ssh.close()
print("✅ Archivo descargado")

# ── 2. Leer CSV ────────────────────────────────────────────
df = pd.read_csv(local_path, encoding="utf-8", sep=",")
print(f"✅ {len(df)} filas leídas del archivo")

# ── 3. Conectar a PostgreSQL ───────────────────────────────
conn = psycopg2.connect(
    host=DB_HOST,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    port=DB_PORT
)
cursor = conn.cursor()

# ── 4. Truncar tabla temp e insertar filas ─────────────────
print("Cargando datos en cirugia_temp...")
cursor.execute("TRUNCATE TABLE internacion.cirugia_temp;")

cols = ",".join(df.columns)
placeholders = ",".join(["%s"] * len(df.columns))

for _, row in df.iterrows():
    cursor.execute(
        f"INSERT INTO internacion.cirugia_temp ({cols}) VALUES ({placeholders})",
        tuple(row)
    )

print(f"✅ {len(df)} filas insertadas en cirugia_temp")

# ── 5. Correr el SQL de procesamiento ─────────────────────
print("Procesando datos hacia internacion.cirugia...")
cursor.execute("""
    INSERT INTO internacion.cirugia (
        nro_episodio, nombre_paciente, fecha_inic_cir, fecha_fin_cir,
        nro_protocolo, quirofano_nro, bacteriologia, rayos_x, implantes,
        infiltracion_con_xilocaina, hora_entr_quir, hora_salida_quir,
        hora_nic_cir, hora_fin_cir, profilaxis, tipo_de_anestesia,
        anatomia_patologica, tipo_cirugia, procedimiento_1, desc_procedimient_1,
        procedimiento_2, desc_procedimiento_2, diagnostico_1, desc_diagnostico_1,
        diagnostico_2, desc_diagnostico_2, cirujano, ayudante_1, ayudant_2,
        ayudant_3, anestesista, instrumentadora_1, instrumentadora_2,
        circulante_1, circulante_2, monitorista, uo_medica,
        fecha_entr_quir, fecha_salida_quir
    )
    SELECT
        nro_episodio,
        nombre_paciente,
        lib.fh(fecha_inic_cir),
        lib.fh(fecha_fin_cir),
        lib.texto_a_entero(nro_protocolo),
        CASE WHEN LENGTH(quirofano_nro)=0 THEN NULL ELSE quirofano_nro END,
        CASE WHEN LENGTH(bacteriologia)=0 THEN NULL ELSE bacteriologia END,
        CASE WHEN LENGTH(rayos_x)=0 THEN NULL ELSE rayos_x END,
        CASE WHEN LENGTH(implantes)=0 THEN NULL ELSE implantes END,
        CASE WHEN LENGTH(infiltracion_con_xilocaina)=0 THEN NULL ELSE infiltracion_con_xilocaina END,
        CAST(hora_entr_quir AS TIME),
        CAST(hora_salida_quir AS TIME),
        CAST(hora_nic_cir AS TIME),
        CAST(hora_fin_cir AS TIME),
        CASE WHEN LENGTH(profilaxis)=0 THEN NULL ELSE profilaxis END,
        CASE WHEN LENGTH(tipo_de_anestesia)=0 THEN NULL ELSE tipo_de_anestesia END,
        CASE WHEN LENGTH(anatomia_patologica)=0 THEN NULL ELSE anatomia_patologica END,
        tipo_cirugia,
        CASE WHEN LENGTH(procedimiento_1)=0 THEN NULL ELSE procedimiento_1 END,
        CASE WHEN LENGTH(desc_procedimient_1)=0 THEN NULL ELSE desc_procedimient_1 END,
        CASE WHEN LENGTH(procedimiento_2)=0 THEN NULL ELSE procedimiento_2 END,
        CASE WHEN LENGTH(desc_procedimiento_2)=0 THEN NULL ELSE desc_procedimiento_2 END,
        CASE WHEN LENGTH(diagnostico_1)=0 THEN NULL ELSE diagnostico_1 END,
        CASE WHEN LENGTH(desc_diagnostico_1)=0 THEN NULL ELSE desc_diagnostico_1 END,
        CASE WHEN LENGTH(diagnostico_2)=0 THEN NULL ELSE diagnostico_2 END,
        CASE WHEN LENGTH(desc_diagnostico_2)=0 THEN NULL ELSE desc_diagnostico_2 END,
        CASE WHEN LENGTH(cirujano)=0 THEN NULL ELSE cirujano END,
        CASE WHEN LENGTH(ayudante_1)=0 THEN NULL ELSE ayudante_1 END,
        CASE WHEN LENGTH(ayudant_2)=0 THEN NULL ELSE ayudant_2 END,
        CASE WHEN LENGTH(ayudant_3)=0 THEN NULL ELSE ayudant_3 END,
        CASE WHEN LENGTH(anestesista)=0 THEN NULL ELSE anestesista END,
        CASE WHEN LENGTH(instrumentadora_1)=0 THEN NULL ELSE instrumentadora_1 END,
        CASE WHEN LENGTH(instrumentadora_2)=0 THEN NULL ELSE instrumentadora_2 END,
        CASE WHEN LENGTH(circulante_1)=0 THEN NULL ELSE circulante_1 END,
        CASE WHEN LENGTH(circulante_2)=0 THEN NULL ELSE circulante_2 END,
        CASE WHEN LENGTH(monitorista)=0 THEN NULL ELSE monitorista END,
        uo_medica,
        lib.fh(fecha_entr_quir),
        lib.fh(fecha_salida_quir)
    FROM internacion.cirugia_temp ct
    WHERE NOT EXISTS (
        SELECT 1 FROM internacion.cirugia
        WHERE nro_protocolo::text = ct.nro_protocolo
    );

    UPDATE internacion.cirugia
    SET tipo_procedimiento = 'Hemodinámico'
    WHERE (uo_medica = 'UQ-HEMD' OR uo_medica = 'UQ-TDOL')
    AND tipo_procedimiento IS NULL;

    UPDATE internacion.cirugia
    SET tipo_procedimiento = 'Quirúrgico'
    WHERE uo_medica != 'UQ-HEMD'
    AND uo_medica != 'UQ-TDOL'
    AND tipo_procedimiento IS NULL;
""")

cursor.execute("SELECT COUNT(*) FROM internacion.cirugia_temp;")
total = cursor.fetchone()[0]
print(f"✅ {total} filas procesadas")

conn.commit()
cursor.close()
conn.close()
print("✅ Carga completada exitosamente")