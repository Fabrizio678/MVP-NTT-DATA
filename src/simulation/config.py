# Constantes de la simulación de reportes ciudadanos VES

# Demografía (Censo INEI 2017, ubigeo 150142)
POBLACION_CENSO_2017 = 393254
MAYORES_EDAD = 279389  # 71%

# Embudo de adopción
TASA_ADOPCION = 0.08
TASA_ACTIVOS = 0.15

# Bounding box VES (rectángulo aproximado, pendiente recorte por shapefile real)
LAT_MIN, LAT_MAX = -12.235, -12.185
LON_MIN, LON_MAX = -76.965, -76.915
LAT_REF = (LAT_MIN + LAT_MAX) / 2  # para proyección grados->metros

# Focos sintéticos: cantidad oficial PIGARS 2024-2028.
# Coordenadas son PLACEHOLDER aleatorio dentro del bbox — pendiente reemplazo
# por los 46 puntos reales geocodificados manualmente desde el PIGARS.
N_HOTSPOTS = 46

DIAS_SIMULACION = 90
SEED = 42

TIPOS = ["desmonte", "reciclaje_domiciliario", "recojo_consolidado"]
TIPOS_PROB = [0.55, 0.25, 0.20]

# Deduplicación espacial (DBSCAN)
EPS_METROS = 30
MIN_SAMPLES = 3
