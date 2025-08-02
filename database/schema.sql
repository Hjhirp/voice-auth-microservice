-- Voice Authentication Microservice Database Schema
-- This script creates the necessary tables for user enrollment and authentication logging

-- Enable the uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for storing voice enrollment data
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone TEXT UNIQUE NOT NULL,
    embedding FLOAT8[192] NOT NULL,
    enrolled_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on phone for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- Create index on id for faster joins
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);

-- Disable Row Level Security for direct access with service key
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Auth attempts table for logging authentication attempts
CREATE TABLE IF NOT EXISTS auth_attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    score FLOAT8 CHECK (score IS NULL OR (score >= 0.0 AND score <= 1.0)),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_auth_attempts_user_id ON auth_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_created_at ON auth_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_auth_attempts_success ON auth_attempts(success);

-- Disable Row Level Security for direct access with service key
ALTER TABLE auth_attempts DISABLE ROW LEVEL SECURITY;

-- Add comments for documentation
COMMENT ON TABLE users IS 'Stores user voice enrollment data with speaker embeddings';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user';
COMMENT ON COLUMN users.phone IS 'User phone number (unique)';
COMMENT ON COLUMN users.embedding IS '192-dimensional speaker embedding from SpeechBrain ECAPA-TDNN';
COMMENT ON COLUMN users.enrolled_at IS 'Timestamp when user was enrolled';

COMMENT ON TABLE auth_attempts IS 'Logs all authentication attempts for auditing';
COMMENT ON COLUMN auth_attempts.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN auth_attempts.user_id IS 'Reference to the user being authenticated';
COMMENT ON COLUMN auth_attempts.success IS 'Whether the authentication attempt was successful';
COMMENT ON COLUMN auth_attempts.score IS 'Voice similarity score (0.0-1.0)';
COMMENT ON COLUMN auth_attempts.created_at IS 'Timestamp of the authentication attempt';