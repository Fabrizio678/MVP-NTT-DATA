# MVP-NTT-DATA — Identificación y Priorización de Puntos Críticos (VES)

TECH CASE

## 1. Problema

Villa El Salvador (VES) no tiene un problema de recolección de residuos, sino de **gestión**: información dispersa, decisiones sin datos, operaciones ineficientes, baja participación ciudadana, baja segregación, escasa valorización.

Eje central del MVP: **identificación y priorización de puntos críticos** de acumulación de residuos en vía pública.

## 2. Restricción dura de datos

No existe un feed abierto de puntos críticos de vía pública para VES. Se relevaron las siguientes fuentes:

| Fuente | Qué da | Estado |
|---|---|---|
| `assets/FICHA_IDENTIFICACION_OEFA.xlsx` (hoja `Universo`) | Registro nacional OEFA de entidades fiscalizables | **Real**. Filtrado a VES (ubigeo `150142`): 9 filas — todas infraestructura formal regulada (rellenos, plantas de transferencia/tratamiento, 1 área degradada), no puntos de vía pública |
| Misma ficha (hoja `BD` / `FICHA_ADR-CD`) | Rúbrica oficial de categorización de áreas degradadas | **Real**, sin data cargada (plantilla vacía). Define 5 criterios mínimos (cerco perimétrico, acceso, área disposición final, estabilidad de taludes, seguridad) + 4 de caracterización (permanencia, volumen, segregación, quema) |
| PIGARS VES 2024-2028 | Los 46 puntos críticos oficiales del distrito | PDF, sin coordenadas — pendiente geocoding manual |
| Inventario Áreas Degradadas OEFA (datosabiertos.gob.pe) | Botaderos con coords, TN/día, área | CSV, probablemente ~0 filas para VES |
| Reporta Residuos (Mapa OEFA) | Alertas ciudadanas validadas | Solo web, sin API |
| INEI 2017 | Demografía, densidad | PDF/shp |
| OSM Overpass | Mercados/ríos/colegios | API abierta real, sin key |

**Conclusión:** la capa operativa de puntos críticos se implementa, no se consume. Esa es la justificación del producto.

## 3. Demografía VES (Censo INEI 2017, ubigeo 150142)

```
poblacion_censo_2017 = 393,254   (M: 193,833 · F: 199,421)
poblacion_proyectada = ~423,000  (crecimiento ~0.3%/año)
superficie_km2       = 35.46
densidad             = ~11,930 hab/km2
mayores_edad         = 279,389 (71%)
```

## 4. Arquitectura de datos (3 capas)

```
CAPA 1  Seed real       → 9 entidades formales OEFA (Universo) + PIGARS 46 pts (pendiente geocoding)
CAPA 2  Stream simulado → reportes ciudadanos (placeholder de WhatsApp/QR/web/app)
                          dedup espacial (DBSCAN ~30m) → 1 foco físico != N reportes
CAPA 3  Priorización    → severidad por reglas (rúbrica FICHA_ADR-CD, no ML)
                          → escala CRITICO / ALTO / MEDIO / BAJO → cola priorizada
```

Motor de BD planificado: **PostgreSQL + PostGIS** (no requerido para este MVP; el pipeline corre en memoria con pandas/numpy/scikit-learn).

## 5. Qué es real vs. qué es simulado

- **Real:** las 9 filas de `Universo` (VES) y la rúbrica de 9 criterios de `FICHA_ADR-CD`/`BD`. No se inventaron coordenadas para estas entidades reguladas — no las tienen en el excel, y fabricarlas sería atribuir ubicación falsa a empresas reales.
- **Simulado:** el stream de reportes ciudadanos y los 46 focos de acumulación (`N_HOTSPOTS` en `config.py`) — no existe feed real de puntos de vía pública, así que se generan sintéticamente dentro del bounding box de VES hasta reemplazarlos por los 46 puntos PIGARS geocodificados.

## 6. Simulación implementada

Unidad de simulación = **reporte georreferenciado**, no habitante.

Embudo de adopción:
```
423k proyectada → 279,389 mayores de edad → ×8% adopción → ×15% activos ≈ 3,353 reportantes
```

- Generador vectorizado (`numpy`, sin loops): 3,353 reportantes → ~7,957 reportes, 85% cae sobre uno de 46 focos sintéticos (distribución pareto: pocos focos grandes, cola larga de chicos), 15% aislados (uniforme en el bbox).
- Dedup espacial: `DBSCAN` (eps=30m, min_samples=3) sobre proyección local grados→metros.
- Clasificación de severidad: top-5 absoluto = `CRITICO`, resto por percentil (`ALTO` ≥ p90, `MEDIO` ≥ p75, `BAJO` el resto).
- Salida: heatmap estático (matplotlib) + mapa interactivo (folium, con leyenda de escala y solo los focos `CRITICO` marcados por default).

## 7. Estructura del proyecto

```
src/simulation/
  config.py            # constantes: demografía, bbox VES, embudo, DBSCAN
  generate_reports.py  # generador vectorizado de reportes ciudadanos
  clustering.py        # DBSCAN dedup + clasificación de severidad
  visualize.py         # heatmap estático + mapa interactivo folium
  run_simulation.py    # pipeline completo (entry point)
data/
  simulated/           # CSVs generados (reportes, puntos críticos)
  output/               # heatmap_estatico.png, mapa_interactivo.html
assets/
  FICHA_IDENTIFICACION_OEFA.xlsx  # fuente real OEFA (Universo + rúbrica BD)
```

## 8. Cómo correr

```powershell
& "C:\Users\User\Documents\NTT MVP\MVP-NTT-DATA\.venv\Scripts\Activate.ps1"
python -m src.simulation.run_simulation
```

Genera/actualiza:
- `data/simulated/reportes_simulados.csv`
- `data/simulated/puntos_criticos_simulados.csv`
- `data/output/heatmap_estatico.png`
- `data/output/mapa_interactivo.html` (abrir directo en el navegador — no embebe en visores con CSP estricto por los tiles externos de Leaflet)

## 9. Principio operativo (blindaje del pitch)

El sistema atiende **densidades, no ciudadanos**. Ningún reporte suelto despacha unidad; se activa por umbral de densidad rentable (break-even). Tres flujos separados por naturaleza del evento:

- Desmonte → cuadrilla municipal batcheada
- Reciclaje domiciliario → acopio / reciclador formal (Ley 29419), costo marginal ≈ 0
- Recojo consolidado → ruta solo sobre umbral; aislados → acopio

## 10. Pendientes

- Geocoding manual de los 46 puntos PIGARS (reemplaza los hotspots sintéticos).
- Parser de las 9 filas reales de `Universo` a tabla seed (capa 1).
- Esquema PostGIS completo (DDL) si se decide persistir en Postgres — no requerido para esta demo.
- Anti-fraude (pHash, dni_hash UNIQUE, geofencing, clustering) — diseñado, no implementado en la simulación actual.

## 11. Límite de entorno

Sandbox de desarrollo sin egress a gob.pe/inei/oefa (403). Descargas de CSV/shapefile/PDF se corren desde la máquina del usuario; acá se generan y prueban los scripts.
