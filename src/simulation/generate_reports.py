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

    # gravedad_real: la severidad técnica de fondo del foco (lo que un técnico
    # certificaría). Correlaciona con el peso (más volumen suele ser más grave)
    # pero no perfecto — el volumen de reportes por sí solo es un proxy ruidoso.
    peso_rank = pd.Series(peso).rank(pct=True).values
    gravedad_real = np.clip(0.5 * peso_rank + 0.5 * rng.random(n), 0, 1)

    return pd.DataFrame({
        "hotspot_id": np.arange(n), "lat": lat, "lon": lon,
        "peso": peso, "gravedad_real": gravedad_real,
    })


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

    # gravedad_real de fondo: la del hotspot asignado, o baseline bajo si es aislado
    gravedad = np.where(
        es_hotspot,
        hotspots.loc[hotspot_idx, "gravedad_real"].values,
        rng.uniform(0, 0.3, n_reportes),
    )

    # señales ciudadanas: observación ruidosa de gravedad_real (subset de FICHA_ADR-CD
    # que un ciudadano SÍ puede aportar; ver README sección 6)
    def _bernoulli_ruidoso(p_base: np.ndarray) -> np.ndarray:
        p_base = np.clip(p_base, 0, 1)
        obs = rng.random(n_reportes) < p_base
        error = rng.random(n_reportes) < cfg.PROB_ERROR_OBSERVACION
        return np.where(error, ~obs, obs)

    operatividad_activo = _bernoulli_ruidoso(0.3 + 0.6 * gravedad)
    quema_observada = _bernoulli_ruidoso(0.05 + 0.5 * gravedad)
    segregacion_observada = _bernoulli_ruidoso(0.10 + 0.4 * gravedad)

    volumen_idx = np.clip((gravedad * 3).astype(int) + rng.integers(-1, 2, n_reportes), 0, 2)
    volumen_categoria = np.array(cfg.VOLUMEN_CATEGORIAS)[volumen_idx]

    permanencia_anios = np.round(np.clip(gravedad * 5 + rng.normal(0, 1, n_reportes), 0, None), 1)

    return pd.DataFrame({
        "reporte_id": np.arange(n_reportes),
        "ciudadano_id": ciudadano_id,
        "lat": lat,
        "lon": lon,
        "tipo": tipo,
        "created_at": created_at,
        "es_hotspot_conocido": es_hotspot,
        "operatividad_activo": operatividad_activo,
        "quema_observada": quema_observada,
        "segregacion_observada": segregacion_observada,
        "volumen_categoria": volumen_categoria,
        "permanencia_anios_estimado": permanencia_anios,
    })


if __name__ == "__main__":
    df = generar_reportes()
    print(f"reportantes: {n_reportantes()} | reportes generados: {len(df)}")
    df.to_csv("data/simulated/reportes_simulados.csv", index=False)
