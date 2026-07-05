"""Ingesta de los CSVs simulados (reportes, puntos_criticos) a Postgres/PostGIS.

Reemplaza el contenido de ambas tablas en cada corrida (mismo criterio que
run_simulation.py: los CSV se regeneran completos, no se appendan).
"""
import os

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

CSV_REPORTES = "data/simulated/reportes_simulados.csv"
CSV_PUNTOS_CRITICOS = "data/simulated/puntos_criticos_simulados.csv"


def _conectar():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def ingestar_reportes(conn, path: str = CSV_REPORTES) -> int:
    df = pd.read_csv(path)
    rows = [
        (
            int(r.reporte_id), int(r.ciudadano_id), r.lon, r.lat, r.tipo, r.created_at,
            bool(r.es_hotspot_conocido), bool(r.operatividad_activo),
            bool(r.quema_observada), bool(r.segregacion_observada),
            r.volumen_categoria, r.permanencia_anios_estimado, int(r.cluster_id),
        )
        for r in df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE reportes RESTART IDENTITY CASCADE")
        execute_values(
            cur,
            """
            INSERT INTO reportes (
                reporte_id, ciudadano_id, ubicacion, tipo, created_at, es_hotspot_conocido,
                operatividad_activo, quema_observada, segregacion_observada,
                volumen_categoria, permanencia_anios_estimado, cluster_id
            ) VALUES %s
            """,
            rows,
            template="(%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, "
                     "%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        )
        cur.execute(
            "SELECT setval('reportes_reporte_id_seq', (SELECT COALESCE(MAX(reporte_id), 1) FROM reportes))"
        )
    conn.commit()
    return len(rows)


def ingestar_puntos_criticos(conn, path: str = CSV_PUNTOS_CRITICOS) -> int:
    df = pd.read_csv(path)
    rows = [
        (
            int(r.cluster_id), r.lon, r.lat, int(r.n_reportes), int(r.n_ciudadanos),
            r.tasa_operatividad, r.tasa_quema, r.tasa_segregacion, r.permanencia_anios,
            r.reincidencia, r.consenso, r.severidad_tecnica, r.score, r.categoria,
        )
        for r in df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE puntos_criticos")
        execute_values(
            cur,
            """
            INSERT INTO puntos_criticos (
                cluster_id, ubicacion, n_reportes, n_ciudadanos, tasa_operatividad,
                tasa_quema, tasa_segregacion, permanencia_anios, reincidencia,
                consenso, severidad_tecnica, score, categoria
            ) VALUES %s
            """,
            rows,
            template="(%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, "
                     "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        )
    conn.commit()
    return len(rows)


def main() -> None:
    conn = _conectar()
    try:
        n_reportes = ingestar_reportes(conn)
        n_puntos = ingestar_puntos_criticos(conn)
        print(f"reportes ingestados: {n_reportes} | puntos_criticos ingestados: {n_puntos}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
