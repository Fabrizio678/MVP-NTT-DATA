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
        tasa_operatividad=("operatividad_activo", "mean"),
        tasa_quema=("quema_observada", "mean"),
        tasa_segregacion=("segregacion_observada", "mean"),
        permanencia_anios=("permanencia_anios_estimado", "mean"),
    ).reset_index()
    resumen["reincidencia"] = resumen["n_reportes"] / resumen["n_ciudadanos"]
    return resumen.sort_values("n_reportes", ascending=False).reset_index(drop=True)


def _consenso(tasa: pd.Series) -> pd.Series:
    """Qué tan de acuerdo están los reportes de un mismo foco en una señal binaria.
    0.5 = mitad dice sí, mitad dice no (máxima incertidumbre). 1.0 = unanimidad."""
    return np.maximum(tasa, 1 - tasa)


def calcular_score(puntos_criticos: pd.DataFrame) -> pd.DataFrame:
    """Score que combina volumen de reportes con señales técnicas ciudadanas y su consenso.
    Reduce el ruido de usar solo n_reportes: un foco con muchos reportes pero señales
    contradictorias (bajo consenso) pesa menos que uno con menos reportes pero
    corroboración fuerte entre ciudadanos independientes."""
    df = puntos_criticos.copy()

    consenso = (
        _consenso(df["tasa_operatividad"]) +
        _consenso(df["tasa_quema"]) +
        _consenso(df["tasa_segregacion"])
    ) / 3  # rango [0.5, 1.0]

    severidad_tecnica = (
        0.4 * df["tasa_operatividad"] +
        0.4 * df["tasa_quema"] +
        0.2 * df["tasa_segregacion"]
    )

    volumen_norm = np.log1p(df["n_reportes"]) / np.log1p(df["n_reportes"].max())

    df["consenso"] = consenso
    df["severidad_tecnica"] = severidad_tecnica
    df["score"] = volumen_norm * severidad_tecnica * consenso
    return df


# Escala de severidad por percentil de n_reportes dentro del propio universo de focos.
# CRITICO = techo real (top_n absoluto); el resto se banda por percentil relativo.
TIERS = [
    ("ALTO", 0.90),
    ("MEDIO", 0.75),
    ("BAJO", 0.0),
]


def clasificar_severidad(puntos_criticos: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Asigna categoría de severidad por `score` (volumen + señal técnica + consenso),
    no por n_reportes crudo. Top N absoluto = CRITICO, resto por percentil de score."""
    df = calcular_score(puntos_criticos)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    p90 = df["score"].quantile(0.90)
    p75 = df["score"].quantile(0.75)

    def _categoria(idx: int, s: float) -> str:
        if idx < top_n:
            return "CRITICO"
        if s >= p90:
            return "ALTO"
        if s >= p75:
            return "MEDIO"
        return "BAJO"

    df["categoria"] = [_categoria(i, s) for i, s in enumerate(df["score"])]
    return df
