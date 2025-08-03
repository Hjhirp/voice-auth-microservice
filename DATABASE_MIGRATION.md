# Database Migration: Switch from UUID to Phone Number Primary Key

This guide shows how to migrate your existing database schema to use phone numbers as the primary key instead of UUIDs.

## ⚠️ IMPORTANT: Backup Your Data First

Before running any migration, **always backup your existing data**:

```sql
-- Create backup tables
CREATE TABLE users_backup AS SELECT * FROM users;
CREATE TABLE auth_attempts_backup AS SELECT * FROM auth_attempts;
```

## Option 1: Fresh Installation (Recommended)

If you haven't deployed to production yet, the easiest approach is to drop and recreate the tables:

### Step 1: Drop Existing Tables

```sql
-- Drop tables in correct order (foreign keys first)
DROP TABLE IF EXISTS auth_attempts;
DROP TABLE IF EXISTS users;
```

### Step 2: Create New Schema

```sql
-- Create users table with phone as primary key
CREATE TABLE users (
    phone VARCHAR(20) PRIMARY KEY,
    embedding FLOAT8[192] NOT NULL,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX idx_users_enrolled_at ON users(enrolled_at);

-- Create auth_attempts table with phone reference
CREATE TABLE auth_attempts (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL REFERENCES users(phone) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    score FLOAT8,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_auth_attempts_phone ON auth_attempts(phone);
CREATE INDEX idx_auth_attempts_created_at ON auth_attempts(created_at);
CREATE INDEX idx_auth_attempts_phone_created ON auth_attempts(phone, created_at DESC);
```

## Option 2: Data Migration (For Production)

If you have existing data that needs to be preserved:

### Step 1: Create New Tables

```sql
-- Create new users table
CREATE TABLE users_new (
    phone VARCHAR(20) PRIMARY KEY,
    embedding FLOAT8[192] NOT NULL,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create new auth_attempts table
CREATE TABLE auth_attempts_new (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL REFERENCES users_new(phone) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    score FLOAT8,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Step 2: Migrate Data

```sql
-- Migrate users data
INSERT INTO users_new (phone, embedding, enrolled_at)
SELECT phone, embedding, enrolled_at
FROM users;

-- Migrate auth_attempts data by joining with users to get phone
INSERT INTO auth_attempts_new (phone, success, score, created_at)
SELECT u.phone, a.success, a.score, a.created_at
FROM auth_attempts a
JOIN users u ON a.user_id = u.id;
```

### Step 3: Verify Migration

```sql
-- Check record counts match
SELECT 'users_old' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'users_new' as table_name, COUNT(*) as count FROM users_new
UNION ALL
SELECT 'auth_attempts_old' as table_name, COUNT(*) as count FROM auth_attempts
UNION ALL
SELECT 'auth_attempts_new' as table_name, COUNT(*) as count FROM auth_attempts_new;

-- Sample data verification
SELECT * FROM users_new LIMIT 5;
SELECT * FROM auth_attempts_new LIMIT 5;
```

### Step 4: Switch Tables

```sql
-- Drop foreign key constraints first
ALTER TABLE auth_attempts DROP CONSTRAINT IF EXISTS auth_attempts_user_id_fkey;

-- Rename tables
ALTER TABLE users RENAME TO users_old;
ALTER TABLE auth_attempts RENAME TO auth_attempts_old;
ALTER TABLE users_new RENAME TO users;
ALTER TABLE auth_attempts_new RENAME TO auth_attempts;
```

### Step 5: Add Indexes

```sql
-- Add performance indexes
CREATE INDEX idx_users_enrolled_at ON users(enrolled_at);
CREATE INDEX idx_auth_attempts_phone ON auth_attempts(phone);
CREATE INDEX idx_auth_attempts_created_at ON auth_attempts(created_at);
CREATE INDEX idx_auth_attempts_phone_created ON auth_attempts(phone, created_at DESC);
```

### Step 6: Cleanup (After Verification)

```sql
-- Only run this after you've verified everything works
DROP TABLE users_old;
DROP TABLE auth_attempts_old;
DROP TABLE users_backup;
DROP TABLE auth_attempts_backup;
```

## Updated Application Configuration

### Environment Variables

No changes needed to environment variables. The same Supabase configuration will work.

### API Changes

The API endpoints have been updated to use phone numbers:

#### Before (UUID-based)
```bash
curl -X POST "/api/v1/enroll-user" \
  -d '{"userId": "123e4567-e89b-12d3-a456-426614174000", "phone": "+1234567890", "audioUrl": "https://..."}'

curl -X POST "/api/v1/verify-password" \
  -d '{"userId": "123e4567-e89b-12d3-a456-426614174000", "listenUrl": "wss://..."}'

curl -X GET "/api/v1/users/123e4567-e89b-12d3-a456-426614174000/auth-history"
```

#### After (Phone-based)
```bash
curl -X POST "/api/v1/enroll-user" \
  -d '{"phone": "+1234567890", "audioUrl": "https://..."}'

curl -X POST "/api/v1/verify-password" \
  -d '{"phone": "+1234567890", "listenUrl": "wss://..."}'

curl -X GET "/api/v1/users/+1234567890/auth-history"
```

## VAPI Integration Changes

### Updated Assistant Prompts

The VAPI assistants no longer need to ask for User IDs. Phone numbers are automatically extracted from the call metadata.

#### Verification Assistant Prompt:
```
You are a voice verification assistant. Your job is to verify user identity through voice authentication.

IMPORTANT INSTRUCTIONS:
1. Greet the user and explain you will verify their identity using their voice
2. DO NOT ask for User ID - the phone number is automatically extracted from the call
3. Once the user confirms they want to verify identity, IMMEDIATELY call the verify_user_voice function
4. The function will automatically analyze their voice during this call for verification
5. Based on the verification result, inform the user if authentication was successful or failed

Remember: Voice analysis happens automatically when you call the function.
```

### Webhook URL Update

Update your VAPI function configuration:

```json
{
  "name": "verify_user_voice",
  "description": "Verify a user's identity by analyzing their voice during this call",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Server URL**: `https://voiceauth-production.up.railway.app/api/v1/vapi-webhook`

## Testing the Migration

### 1. Test User Enrollment

```bash
curl -X POST "https://voiceauth-production.up.railway.app/api/v1/enroll-user" \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: test-123" \
  -d '{
    "phone": "+1234567890",
    "audioUrl": "https://example.com/sample-voice.wav"
  }'
```

### 2. Test VAPI Webhook

```bash
curl -X POST "https://voiceauth-production.up.railway.app/api/v1/vapi-webhook/debug" \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: test-456" \
  -d '{
    "message": {
      "call": {
        "customer": {"number": "+1234567890"},
        "monitor": {"listenUrl": "wss://api.vapi.ai/call/listen/abc123"}
      }
    }
  }'
```

### 3. Test Authentication History

```bash
curl -X GET "https://voiceauth-production.up.railway.app/api/v1/users/+1234567890/auth-history" \
  -H "X-Call-ID: test-789"
```

## Benefits of Phone Number Primary Key

1. **Simplified Integration**: No need to manage separate User IDs
2. **Natural Identifier**: Phone numbers are naturally unique and meaningful
3. **VAPI Compatibility**: Phone numbers are automatically available in VAPI calls
4. **User-Friendly**: Easier for users and administrators to reference
5. **Reduced Complexity**: Fewer fields to manage and validate

## Rollback Plan

If you need to rollback to the UUID-based system:

1. Keep the backup tables (`users_backup`, `auth_attempts_backup`)
2. Rename current tables to `_phone` suffix
3. Restore backup tables to original names
4. Deploy the previous version of the application

```sql
-- Rollback commands
ALTER TABLE users RENAME TO users_phone;
ALTER TABLE auth_attempts RENAME TO auth_attempts_phone;
ALTER TABLE users_backup RENAME TO users;
ALTER TABLE auth_attempts_backup RENAME TO auth_attempts;
```