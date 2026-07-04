"""Corre el pipeline completo: genera reportes -> clusteriza -> exporta mapa de calor."""
from src.simulation.clustering import clasificar_severidad, clusterizar, resumen_puntos_criticos
from src.simulation.generate_reports import generar_reportes, n_reportantes
from src.simulation.visualize import mapa_calor_estatico, mapa_interactivo

CSV_REPORTES = "data/simulated/reportes_simulados.csv"
CSV_PUNTOS_CRITICOS = "data/simulated/puntos_criticos_simulados.csv"
PNG_HEATMAP = "data/output/heatmap_estatico.png"
HTML_MAPA = "data/output/mapa_interactivo.html"


def main() -> None:
    reportes = generar_reportes()
    print(f"reportantes: {n_reportantes()} | reportes generados: {len(reportes)}")

    reportes_cl = clusterizar(reportes)
    puntos_criticos = clasificar_severidad(resumen_puntos_criticos(reportes_cl), top_n=5)
    n_aislados = int((reportes_cl["cluster_id"] == -1).sum())
    print(f"focos físicos detectados: {len(puntos_criticos)} | reportes aislados: {n_aislados}")
    print(puntos_criticos["categoria"].value_counts())

    reportes_cl.to_csv(CSV_REPORTES, index=False)
    puntos_criticos.to_csv(CSV_PUNTOS_CRITICOS, index=False)

    mapa_calor_estatico(reportes, PNG_HEATMAP)
    mapa_interactivo(reportes, puntos_criticos, HTML_MAPA)
    print(f"heatmap estático: {PNG_HEATMAP}")
    print(f"mapa interactivo: {HTML_MAPA}")


if __name__ == "__main__":
    main()
