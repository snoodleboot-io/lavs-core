CREATE TABLE IF NOT EXISTS Versions (
    major INTEGER,
    minor INTEGER,
    patch INTEGER,
    product_name VARCHAR,
    id INTEGER PRIMARY KEY,
    status VARCHAR DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back'))
);

ALTER TABLE Versions ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active';

CREATE SEQUENCE IF NOT EXISTS version_id_seq START 1;
