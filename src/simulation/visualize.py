"""Mapa de calor de reportes ciudadanos simulados."""
import pandas as pd


def mapa_calor_estatico(reportes: pd.DataFrame, out_path: str) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 8))
    hb = ax.hexbin(reportes["lon"], reportes["lat"], gridsize=60, cmap="inferno", mincnt=1)
    fig.colorbar(hb, ax=ax, label="Reportes acumulados")
    ax.set_title("Densidad de reportes ciudadanos simulados — Villa El Salvador")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


COLOR_TIER = {
    "CRITICO": "#d7191c",
    "ALTO": "#fdae61",
    "MEDIO": "#ffffbf",
    "BAJO": "#a6d96a",
}

_LEYENDA_HTML = """
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
            background: white; padding: 10px 14px; border: 1px solid #999;
            border-radius: 4px; font-size: 13px; line-height: 1.6;">
  <b>Severidad (por reportes acumulados)</b><br>
  <span style="color:#d7191c;">&#9679;</span> CRITICO (top prioridad)<br>
  <span style="color:#fdae61;">&#9679;</span> ALTO<br>
  <span style="color:#ffffbf;">&#9679;</span> MEDIO<br>
  <span style="color:#a6d96a;">&#9679;</span> BAJO
</div>
"""


def mapa_interactivo(
    reportes: pd.DataFrame,
    puntos_criticos: pd.DataFrame,
    out_path: str,
    tiers_visibles: tuple[str, ...] = ("CRITICO",),
) -> None:
    """tiers_visibles controla qué categorías se marcan en el mapa (default: solo CRITICO)."""
    import folium
    from folium.plugins import HeatMap

    centro = [reportes["lat"].mean(), reportes["lon"].mean()]
    m = folium.Map(location=centro, zoom_start=14, tiles="cartodbpositron")
    HeatMap(reportes[["lat", "lon"]].values.tolist(), radius=12, blur=18).add_to(m)

    visibles = puntos_criticos[puntos_criticos["categoria"].isin(tiers_visibles)]
    for _, row in visibles.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6 + min(row["n_reportes"], 1800) / 100,
            color=COLOR_TIER[row["categoria"]],
            fill=True,
            fill_color=COLOR_TIER[row["categoria"]],
            fill_opacity=0.85,
            weight=2,
            popup=(
                f"Foco #{int(row['cluster_id'])} | {row['categoria']} | "
                f"{int(row['n_reportes'])} reportes | score {row['score']:.2f} | "
                f"consenso {row['consenso']:.0%}"
            ),
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(_LEYENDA_HTML))
    m.save(out_path)
