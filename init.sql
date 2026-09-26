CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════════════════
-- TABLAS PRINCIPALES
-- ═══════════════════════════════════════════════════════════

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    perfil_marca TEXT,
    restricciones_tono TEXT,
    historico TEXT,
    embedding VECTOR(768)
);

CREATE TABLE tendencias (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(100),
    content TEXT,
    fuente VARCHAR(50) DEFAULT 'interna',
    fecha DATE DEFAULT CURRENT_DATE,
    embedding VECTOR(768)
);

CREATE TABLE referencias_competencia (
    id SERIAL PRIMARY KEY,
    competidor VARCHAR(100),
    content TEXT,
    plataforma VARCHAR(50),
    embedding VECTOR(768)
);

CREATE TABLE ideas_generadas (
    id SERIAL PRIMARY KEY,
    client_id INT,
    content TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE publicaciones_generadas (
    id SERIAL PRIMARY KEY,
    client_id INT,
    idea_id INT,
    content TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- ÍNDICES PARA BÚSQUEDA VECTORIAL RÁPIDA (IVFFlat)
-- Se crean después de tener datos; por ahora un índice simple
-- ═══════════════════════════════════════════════════════════

CREATE INDEX idx_ideas_embedding ON ideas_generadas
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ═══════════════════════════════════════════════════════════
-- DATOS DE EJEMPLO (seed)
-- ═══════════════════════════════════════════════════════════

INSERT INTO clientes (nombre, perfil_marca, restricciones_tono, historico) VALUES
('EcoBrand', 
 'Marca de productos ecológicos y sostenibles dirigida a millennials conscientes del medio ambiente. Valores: sostenibilidad, transparencia, innovación verde.',
 'Tono: cercano pero profesional. Evitar greenwashing. No usar mayúsculas excesivas ni signos de exclamación múltiples. Incluir datos o hechos cuando sea posible.',
 'Campañas anteriores: "Reto Zero Waste" (2025, +340% engagement), "Cada Gota Cuenta" (2025, viral en TikTok). El público responde bien al storytelling personal.'),

('TechStart', 
 'Startup de tecnología financiera (fintech) que simplifica pagos para pequeñas empresas en Latinoamérica. Valores: accesibilidad, seguridad, velocidad.',
 'Tono: joven, directo, confiable. Usar datos y cifras. Evitar jerga técnica excesiva. Incluir llamados a la acción claros.',
 'Campañas anteriores: "Pagos sin Fricción" (2025, 15K leads), "Tu Negocio en tu Bolsillo" (2024, 8K descargas). El público prefiere contenido corto y visual.'),

('FitLife', 
 'Marca de nutrición y fitness con suplementos naturales y planes de entrenamiento personalizados. Valores: salud integral, ciencia, comunidad.',
 'Tono: motivador pero no agresivo. Basar afirmaciones en ciencia. No prometer resultados milagrosos. Incluir testimonios reales.',
 'Campañas anteriores: "30 Días de Cambio" (2025, 22K participantes), "Nutre tu Mente" (2025, boost en ventas del 45%).');
