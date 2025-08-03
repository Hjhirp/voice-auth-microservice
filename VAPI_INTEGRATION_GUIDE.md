# VAPI Dashboard Integration Guide

This guide shows how to integrate your voice authentication microservice with VAPI using the VAPI Dashboard for complete voice authentication system.

## 🚀 Deployed Service

**Base URL:** `https://voiceauth-production.up.railway.app`

**API Documentation:** `https://voiceauth-production.up.railway.app/docs`

**Health Check:** `https://voiceauth-production.up.railway.app/healthz`

## 📋 Prerequisites

1. **VAPI Account**: Sign up at [vapi.ai](https://vapi.ai)
2. **VAPI Dashboard Access**: Login to your VAPI dashboard
3. **Phone Number**: A phone number for testing voice calls (optional for web)

## 🎯 VAPI Dashboard Setup

### 1. Create Voice Enrollment Assistant in VAPI Dashboard

**Step 1: Go to Assistants → Create New Assistant**

**Basic Configuration:**
- **Name**: `Voice Enrollment Assistant`
- **Description**: `Enrolls users for voice authentication by recording their voice sample`

**Model Configuration:**
- **Provider**: OpenAI
- **Model**: `gpt-4o-mini` (recommended for better function calling)
- **Temperature**: `0.3` (lower for more consistent responses)

**System Message:**
```
You are a voice enrollment assistant. Your job is to guide users through voice enrollment for authentication.

IMPORTANT INSTRUCTIONS:
1. Always greet the user and explain you will help them enroll their voice
2. Ask for their User ID and phone number if not provided
3. Once you have the required information, IMMEDIATELY call the enroll_user_voice function
4. The function will automatically capture their voice during this call - no need to ask them to speak again
5. Keep responses brief and professional
6. If enrollment succeeds, congratulate them and explain they can now use voice authentication
7. If enrollment fails, explain the issue and offer to try again

Remember: The voice recording happens automatically when you call the function - don't ask users to speak separately.
```

**Voice Configuration:**
- **Provider**: 11Labs (recommended) or OpenAI
- **Voice**: Choose a clear, professional voice
- **Speed**: `1.0`
- **Stability**: `0.7`

**Functions to Add:**

**Function 1: enroll_user_voice**
```json
{
  "name": "enroll_user_voice",
  "description": "Enroll a user's voice for authentication by capturing their voice during this call",
  "parameters": {
    "type": "object",
    "properties": {
      "userId": {
        "type": "string",
        "description": "Unique identifier for the user"
      },
      "phone": {
        "type": "string",
        "description": "User's phone number in E.164 format (e.g., +1234567890)"
      }
    },
    "required": ["userId", "phone"]
  }
}
```

**Function Calling Configuration:**
- **Server URL**: `https://voiceauth-production.up.railway.app/api/v1/vapi-webhook`
- **Server URL Secret**: `your-secure-webhook-secret-123`

### 2. Create Voice Verification Assistant in VAPI Dashboard

**Step 1: Go to Assistants → Create New Assistant**

**Basic Configuration:**
- **Name**: `Voice Verification Assistant`
- **Description**: `Verifies user identity through voice authentication`

**Model Configuration:**
- **Provider**: OpenAI
- **Model**: `gpt-4o-mini`
- **Temperature**: `0.3`

**System Message:**
```
You are a voice verification assistant. Your job is to verify user identity through voice authentication.

IMPORTANT INSTRUCTIONS:
1. Greet the user and explain you will verify their identity using their voice
2. Ask for their User ID if not provided
3. Once you have the User ID, IMMEDIATELY call the verify_user_voice function
4. The function will automatically analyze their voice during this call for verification
5. Based on the verification result, inform the user if authentication was successful or failed
6. Keep responses brief and professional
7. If verification fails, offer to try again or suggest they re-enroll if needed

Remember: Voice analysis happens automatically when you call the function - don't ask users to speak separately.
```

**Voice Configuration:**
- **Provider**: 11Labs or OpenAI
- **Voice**: Same as enrollment assistant for consistency
- **Speed**: `1.0`
- **Stability**: `0.7`

**Functions to Add:**

**Function 1: verify_user_voice**
```json
{
  "name": "verify_user_voice", 
  "description": "Verify a user's identity by analyzing their voice during this call",
  "parameters": {
    "type": "object",
    "properties": {
      "userId": {
        "type": "string",
        "description": "Unique identifier for the user to verify"
      }
    },
    "required": ["userId"]
  }
}
```

**Function Calling Configuration:**
- **Server URL**: `https://voiceauth-production.up.railway.app/api/v1/vapi-webhook`
- **Server URL Secret**: `your-secure-webhook-secret-123`

### 3. Phone Number Setup (Optional)

**For Phone Calls:**
1. Go to **Phone Numbers** in VAPI Dashboard
2. **Buy a phone number** or configure existing one
3. **Assign assistants** to the phone number:
   - **Inbound**: Set to enrollment or verification assistant
   - **Outbound**: Configure for calling users

### 4. Web Widget Setup

**For Web Integration:**
1. Go to **Web** in VAPI Dashboard  
2. **Create Web Widget**
3. **Configure assistants** for web calls
4. **Copy embed code** for your website

## 🔄 How the Voice Recording Works

### Automatic Voice Capture Process

**Important**: VAPI automatically records the conversation audio during function calls. Here's the flow:

#### Enrollment Flow:
1. User calls/connects to enrollment assistant
2. Assistant asks for User ID and phone number
3. Assistant calls `enroll_user_voice()` function 
4. **VAPI automatically captures the ongoing call audio**
5. Your service receives the audio via webhook and processes it
6. User's voice profile is stored for future verification

#### Verification Flow:
1. User calls/connects to verification assistant  
2. Assistant asks for User ID
3. Assistant calls `verify_user_voice()` function
4. **VAPI automatically captures the ongoing call audio**
5. Your service compares the audio with stored voice profile
6. Authentication result is returned to user

### Key Points:
- ✅ **No separate recording step needed** - VAPI captures call audio automatically
- ✅ **Seamless user experience** - Users just talk naturally during the call
- ✅ **Real-time processing** - Authentication happens during the conversation
- ✅ **Security** - Audio is processed immediately and not stored permanently

## 🌐 Dashboard Integration Options

Use the VAPI Dashboard to:
- **Monitor all calls** and conversations
- **View call analytics** and success rates  
- **Manage assistants** and update prompts
- **Configure phone numbers** and web widgets
- **Review call logs** and transcripts
- **Track function calls** and responses

### Option 2: Custom Dashboard Integration

If you need a custom dashboard, you can integrate with VAPI's REST API:

```javascript
// Get call history
const response = await fetch('https://api.vapi.ai/call', {
  headers: {
    'Authorization': 'Bearer your-vapi-api-key'
  }
});

// Get call details
const call = await fetch(`https://api.vapi.ai/call/${callId}`, {
  headers: {
    'Authorization': 'Bearer your-vapi-api-key'
  }
});
```

### Option 2: React Integration

```jsx
import React, { useState } from 'react';
import { Vapi } from '@vapi-ai/web';

const VoiceAuthComponent = () => {
    const [vapi] = useState(() => new Vapi('your-vapi-public-key'));
    const [userId, setUserId] = useState('');
    const [phone, setPhone] = useState('');
    const [status, setStatus] = useState('');
    const [isCallActive, setIsCallActive] = useState(false);

    const startEnrollment = async () => {
        if (!userId || !phone) {
            alert('Please enter both User ID and phone number');
            return;
        }

        try {
            setStatus('📞 Starting voice enrollment...');
            setIsCallActive(true);

            const call = await vapi.start({
                assistantId: 'your-enrollment-assistant-id',
                metadata: {
                    userId,
                    phone,
                    action: 'enrollment'
                }
            });

            call.on('call-end', (data) => {
                setStatus('✅ Enrollment completed!');
                setIsCallActive(false);
                console.log('Enrollment result:', data);
            });

            call.on('error', (error) => {
                setStatus('❌ Enrollment failed: ' + error.message);
                setIsCallActive(false);
            });

        } catch (error) {
            setStatus('❌ Failed to start call: ' + error.message);
            setIsCallActive(false);
        }
    };

    const startVerification = async () => {
        if (!userId) {
            alert('Please enter User ID');
            return;
        }

        try {
            setStatus('📞 Starting voice verification...');
            setIsCallActive(true);

            const call = await vapi.start({
                assistantId: 'your-verification-assistant-id',
                metadata: {
                    userId,
                    action: 'verification'
                }
            });

            call.on('call-end', (data) => {
                if (data.success) {
                    setStatus('✅ Voice verification successful!');
                } else {
                    setStatus('❌ Voice verification failed');
                }
                setIsCallActive(false);
                console.log('Verification result:', data);
            });

            call.on('error', (error) => {
                setStatus('❌ Verification failed: ' + error.message);
                setIsCallActive(false);
            });

        } catch (error) {
            setStatus('❌ Failed to start call: ' + error.message);
            setIsCallActive(false);
        }
    };

    return (
        <div className="voice-auth-container">
            <h1>Voice Authentication System</h1>
            
            <div className="enrollment-section">
                <h2>Voice Enrollment</h2>
                <input
                    type="text"
                    placeholder="User ID"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    disabled={isCallActive}
                />
                <input
                    type="text"
                    placeholder="Phone Number"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    disabled={isCallActive}
                />
                <button 
                    onClick={startEnrollment}
                    disabled={isCallActive}
                >
                    {isCallActive ? 'Call in Progress...' : 'Start Voice Enrollment'}
                </button>
            </div>

            <div className="verification-section">
                <h2>Voice Verification</h2>
                <input
                    type="text"
                    placeholder="User ID"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    disabled={isCallActive}
                />
                <button 
                    onClick={startVerification}
                    disabled={isCallActive}
                >
                    {isCallActive ? 'Call in Progress...' : 'Verify Voice'}
                </button>
            </div>

            <div className="status">
                {status}
            </div>
        </div>
    );
};

export default VoiceAuthComponent;
```

## 🔗 Backend Webhook Handler

You'll need to handle VAPI webhooks in your backend. The service already includes webhook endpoints:

```python
# Already implemented in src/api/vapi.py
@router.post("/vapi-webhook")
async def handle_vapi_webhook(webhook_data: dict):
    # Handles function calls from VAPI
    # Routes to appropriate enrollment/verification functions
    pass
```

## 📱 Phone Integration

### Inbound Calls Setup

1. **Get a Phone Number** from VAPI dashboard
2. **Configure Assistant** for the phone number
3. **Set up Call Flow**:

```json
{
  "phoneNumber": "+1234567890",
  "assistantId": "your-voice-auth-assistant-id",
  "serverUrl": "https://voiceauth-production.up.railway.app/api/v1/vapi-webhook"
}
```

### Outbound Calls

```javascript
// Trigger outbound enrollment call
async function callUserForEnrollment(userId, phone) {
    const response = await fetch('https://api.vapi.ai/call', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer your-vapi-api-key',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            assistantId: 'your-enrollment-assistant-id',
            customer: {
                number: phone
            },
            metadata: {
                userId: userId,
                action: 'enrollment'
            }
        })
    });
    
    return response.json();
}
```

## 🧪 Testing Your Integration

### 1. Test Health Endpoint
```bash
curl https://voiceauth-production.up.railway.app/healthz
```

### 2. Test Enrollment API
```bash
curl -X POST https://voiceauth-production.up.railway.app/api/v1/enroll-user \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: test-123" \
  -d '{
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "phone": "+1234567890",
    "audioUrl": "https://example.com/sample-voice.wav"
  }'
```

### 3. Test Verification API  
```bash
curl -X POST https://voiceauth-production.up.railway.app/api/v1/verify-password \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: test-456" \
  -d '{
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "listenUrl": "wss://api.vapi.ai/call/listen/abc123"
  }'
```

## 🔐 Security Best Practices

1. **API Keys**: Store VAPI keys securely (environment variables)
2. **Webhook Security**: Validate webhook signatures from VAPI
3. **HTTPS Only**: Always use HTTPS endpoints
4. **Rate Limiting**: Implement rate limiting for enrollment/verification
5. **User Validation**: Verify user ownership before enrollment

## 🚀 Next Steps

1. **Set up VAPI account** and get API keys
2. **Create assistants** for enrollment and verification
3. **Configure phone numbers** in VAPI dashboard
4. **Deploy frontend** with your domain
5. **Test end-to-end flow** with real phone calls

Your voice authentication system is now ready for production use!