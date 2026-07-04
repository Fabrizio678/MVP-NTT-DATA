"""Generador vectorizado de reportes ciudadanos simulados para VES.

Unidad de simulación = reporte georreferenciado, no habitante.
Embudo: mayores de edad -> adopción -> activos -> reportantes.
"""
import numpy as np
import pandas as pd

from . import config as cfg


def n_reportantes() -> int:
    return int(round(cfg.MAYORES_EDAD * cfg.TASA_ADOPCION * cfg.TASA_ACTIVOS))


def generar_hotspots(rng: np.random.Generator, n: int = cfg.N_HOTSPOTS) -> pd.DataFrame:
    """Focos sintéticos de acumulación (placeholder hasta geocodificar los 46 puntos PIGARS)."""
    lat = rng.uniform(cfg.LAT_MIN, cfg.LAT_MAX, n)
    lon = rng.uniform(cfg.LON_MIN, cfg.LON_MAX, n)
    # pocos focos grandes, cola larga de focos chicos
    peso = rng.pareto(a=2.0, size=n) + 0.3
    peso = peso / peso.sum()
    return pd.DataFrame({"hotspot_id": np.arange(n), "lat": lat, "lon": lon, "peso": peso})


def generar_reportes(seed: int = cfg.SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_rep = n_reportantes()
    hotspots = generar_hotspots(rng)

    reportes_por_reportante = rng.poisson(lam=1.4, size=n_rep) + 1
    n_reportes = int(reportes_por_reportante.sum())
    ciudadano_id = np.repeat(np.arange(n_rep), reportes_por_reportante)

    # 85% de reportes cae sobre un hotspot conocido, 15% son aislados (uniformes)
    es_hotspot = rng.random(n_reportes) < 0.85
    hotspot_idx = rng.choice(hotspots["hotspot_id"].values, size=n_reportes, p=hotspots["peso"].values)

    lat = np.empty(n_reportes)
    lon = np.empty(n_reportes)

    # dispersión gaussiana ~30-80m alrededor del hotspot
    std_m = rng.uniform(30, 80, n_reportes)
    std_deg = std_m / 111_320

    lat_hotspot = hotspots.loc[hotspot_idx, "lat"].values
    lon_hotspot = hotspots.loc[hotspot_idx, "lon"].values

    lat[es_hotspot] = rng.normal(lat_hotspot[es_hotspot], std_deg[es_hotspot])
    lon[es_hotspot] = rng.normal(lon_hotspot[es_hotspot], std_deg[es_hotspot])

    n_aislados = int((~es_hotspot).sum())
    lat[~es_hotspot] = rng.uniform(cfg.LAT_MIN, cfg.LAT_MAX, n_aislados)
    lon[~es_hotspot] = rng.uniform(cfg.LON_MIN, cfg.LON_MAX, n_aislados)

    lat = np.clip(lat, cfg.LAT_MIN, cfg.LAT_MAX)
    lon = np.clip(lon, cfg.LON_MIN, cfg.LON_MAX)

    tipo = rng.choice(cfg.TIPOS, size=n_reportes, p=cfg.TIPOS_PROB)
    dia_offset = rng.integers(0, cfg.DIAS_SIMULACION, n_reportes)
    created_at = pd.Timestamp.now().normalize() - pd.to_timedelta(dia_offset, unit="D")

    return pd.DataFrame({
        "reporte_id": np.arange(n_reportes),
        "ciudadano_id": ciudadano_id,
        "lat": lat,
        "lon": lon,
        "tipo": tipo,
        "created_at": created_at,
        "es_hotspot_conocido": es_hotspot,
    })


if __name__ == "__main__":
    df = generar_reportes()
    print(f"reportantes: {n_reportantes()} | reportes generados: {len(df)}")
    df.to_csv("data/simulated/reportes_simulados.csv", index=False)
