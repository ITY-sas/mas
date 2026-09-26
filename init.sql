CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    perfil_marca TEXT,
    restricciones_tono TEXT,
    historico TEXT
);

CREATE TABLE ideas_generadas (
    id SERIAL PRIMARY KEY,
    client_id INT,
    content TEXT,
    embedding VECTOR(1536),
    client_id INT,
    content TEXT,
    embedding VECTOR(1536),
);

CREATE TABLE tendencias (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536),
);

CREATE TABLE referencias_competencia (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536),
);
