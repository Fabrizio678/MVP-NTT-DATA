-- Esquema MVP-NTT-DATA: puntos críticos VES (PostGIS)
-- Basado en el pipeline actual (src/simulation/*) + extensión de reciclaje/incentivos (README §12)

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE recicladores (
    reciclador_id       BIGSERIAL PRIMARY KEY,
    nombre              TEXT NOT NULL,
    ubigeo_zona         CHAR(6),
    puntos_acumulados   INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reportes (
    reporte_id                  BIGSERIAL PRIMARY KEY,
    ciudadano_id                BIGINT NOT NULL,
    ubicacion                   GEOGRAPHY(POINT, 4326) NOT NULL,
    ubigeo                      CHAR(6),
    tipo                        TEXT NOT NULL
        CHECK (tipo IN ('desmonte', 'reciclaje_domiciliario', 'recojo_consolidado')),
    tipo_material               TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    es_hotspot_conocido         BOOLEAN NOT NULL DEFAULT false,
    operatividad_activo         BOOLEAN,
    quema_observada             BOOLEAN,
    segregacion_observada       BOOLEAN,
    volumen_categoria           TEXT CHECK (volumen_categoria IN ('bajo', 'medio', 'alto')),
    permanencia_anios_estimado  NUMERIC(5, 1),
    foto_url                    TEXT,
    foto_hash                   TEXT,
    reciclador_id               BIGINT REFERENCES recicladores(reciclador_id),
    estado_corroboracion        TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado_corroboracion IN ('pendiente', 'corroborado', 'rechazado')),
    puntos_otorgados            INTEGER NOT NULL DEFAULT 0,
    cluster_id                  INTEGER
);

CREATE INDEX idx_reportes_ubicacion ON reportes USING GIST (ubicacion);
CREATE INDEX idx_reportes_ubigeo ON reportes (ubigeo);
CREATE INDEX idx_reportes_cluster_id ON reportes (cluster_id);
CREATE INDEX idx_reportes_estado_corroboracion ON reportes (estado_corroboracion);

CREATE TABLE puntos_criticos (
    cluster_id          INTEGER PRIMARY KEY,
    ubicacion           GEOGRAPHY(POINT, 4326) NOT NULL,
    ubigeo              CHAR(6),
    n_reportes          INTEGER NOT NULL,
    n_ciudadanos        INTEGER NOT NULL,
    tasa_operatividad   NUMERIC(4, 3),
    tasa_quema          NUMERIC(4, 3),
    tasa_segregacion    NUMERIC(4, 3),
    permanencia_anios   NUMERIC(5, 1),
    reincidencia        NUMERIC(6, 3),
    consenso            NUMERIC(4, 3),
    severidad_tecnica   NUMERIC(4, 3),
    score               NUMERIC(6, 5),
    categoria           TEXT NOT NULL CHECK (categoria IN ('CRITICO', 'ALTO', 'MEDIO', 'BAJO')),
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_puntos_criticos_ubicacion ON puntos_criticos USING GIST (ubicacion);
CREATE INDEX idx_puntos_criticos_categoria ON puntos_criticos (categoria);

CREATE TABLE ledger_puntos (
    id              BIGSERIAL PRIMARY KEY,
    reporte_id      BIGINT NOT NULL REFERENCES reportes(reporte_id),
    reciclador_id   BIGINT REFERENCES recicladores(reciclador_id),
    puntos          INTEGER NOT NULL,
    motivo          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_puntos_reporte_id ON ledger_puntos (reporte_id);
CREATE INDEX idx_ledger_puntos_reciclador_id ON ledger_puntos (reciclador_id);
