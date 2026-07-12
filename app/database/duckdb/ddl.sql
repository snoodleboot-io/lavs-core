-- LAVS core schema (DuckDB dialect).
-- ULID identifiers are stored as VARCHAR; foreign keys are modelled as plain
-- VARCHAR columns referencing the parent table's id.

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    base_version VARCHAR NOT NULL DEFAULT '0.0.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Idempotently upgrade databases created before base_version existed.
ALTER TABLE products ADD COLUMN IF NOT EXISTS base_version VARCHAR DEFAULT '0.0.0';

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

CREATE TABLE IF NOT EXISTS releases (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    product_version VARCHAR NOT NULL,
    label VARCHAR,
    notes VARCHAR,
    idempotency_key VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS release_components (
    release_id VARCHAR NOT NULL REFERENCES releases(id),
    component_id VARCHAR NOT NULL,
    version_id VARCHAR NOT NULL,
    PRIMARY KEY (release_id, component_id)
);

-- Auth (P4): password/session users and their opaque, hashed tokens.
-- Passwords are stored as argon2id hashes; session and verification tokens are
-- stored only as their SHA-256 hashes (the raw token is never persisted).
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
    edition VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    token_hash VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_hash VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP
);
