"""Deduplicación espacial de reportes en focos físicos (DBSCAN).

1 foco físico != N reportes. Reportes fuera de un cluster (label -1) son
aislados: no arman foco, se derivan a acopio en vez de ruta consolidada.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from . import config as cfg


def _a_metros(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Proyección equirectangular local (válida para distancias < 5 km)."""
    m_por_grado_lat = 111_320
    m_por_grado_lon = 111_320 * np.cos(np.radians(cfg.LAT_REF))
    x = lon * m_por_grado_lon
    y = lat * m_por_grado_lat
    return np.column_stack([x, y])


def clusterizar(reportes: pd.DataFrame) -> pd.DataFrame:
    coords_m = _a_metros(reportes["lat"].values, reportes["lon"].values)
    labels = DBSCAN(eps=cfg.EPS_METROS, min_samples=cfg.MIN_SAMPLES).fit_predict(coords_m)
    reportes = reportes.copy()
    reportes["cluster_id"] = labels
    return reportes


def resumen_puntos_criticos(reportes_clusterizados: pd.DataFrame) -> pd.DataFrame:
    focos = reportes_clusterizados[reportes_clusterizados["cluster_id"] != -1]
    resumen = focos.groupby("cluster_id").agg(
        lat=("lat", "mean"),
        lon=("lon", "mean"),
        n_reportes=("reporte_id", "count"),
        n_ciudadanos=("ciudadano_id", "nunique"),
    ).reset_index()
    resumen["reincidencia"] = resumen["n_reportes"] / resumen["n_ciudadanos"]
    return resumen.sort_values("n_reportes", ascending=False).reset_index(drop=True)


# Escala de severidad por percentil de n_reportes dentro del propio universo de focos.
# CRITICO = techo real (top_n absoluto); el resto se banda por percentil relativo.
TIERS = [
    ("ALTO", 0.90),
    ("MEDIO", 0.75),
    ("BAJO", 0.0),
]


def clasificar_severidad(puntos_criticos: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Asigna categoría de severidad. Top N absoluto = CRITICO, resto por percentil."""
    df = puntos_criticos.sort_values("n_reportes", ascending=False).reset_index(drop=True)
    p90 = df["n_reportes"].quantile(0.90)
    p75 = df["n_reportes"].quantile(0.75)

    def _categoria(idx: int, n: int) -> str:
        if idx < top_n:
            return "CRITICO"
        if n >= p90:
            return "ALTO"
        if n >= p75:
            return "MEDIO"
        return "BAJO"

    df["categoria"] = [_categoria(i, n) for i, n in enumerate(df["n_reportes"])]
    return df
