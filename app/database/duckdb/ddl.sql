-- LAVS core schema (DuckDB dialect).
-- ULID identifiers are stored as VARCHAR; foreign keys are modelled as plain
-- VARCHAR columns referencing the parent table's id.

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS components (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli'))
);

CREATE TABLE IF NOT EXISTS versions (
    id VARCHAR PRIMARY KEY,
    component_id VARCHAR NOT NULL REFERENCES components(id),
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR,
    status VARCHAR DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
