-- Initial schema migration for voice authentication microservice
-- Run this script to set up the database tables

BEGIN;

-- Enable the uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for storing voice enrollment data
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone TEXT UNIQUE NOT NULL,
    embedding FLOAT8[192] NOT NULL,
    enrolled_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_id ON users(id);

-- Disable Row Level Security for direct access with service key
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Auth attempts table for logging authentication attempts
CREATE TABLE auth_attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    score FLOAT8 CHECK (score IS NULL OR (score >= 0.0 AND score <= 1.0)),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_auth_attempts_user_id ON auth_attempts(user_id);
CREATE INDEX idx_auth_attempts_created_at ON auth_attempts(created_at);
CREATE INDEX idx_auth_attempts_success ON auth_attempts(success);

-- Disable Row Level Security for direct access with service key
ALTER TABLE auth_attempts DISABLE ROW LEVEL SECURITY;

-- Add table comments
COMMENT ON TABLE users IS 'Stores user voice enrollment data with speaker embeddings';
COMMENT ON TABLE auth_attempts IS 'Logs all authentication attempts for auditing';

COMMIT;