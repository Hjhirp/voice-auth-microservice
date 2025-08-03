"""
Streamlit Dashboard for Voice Authentication User Enrollment
"""

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import time
from typing import Dict, List, Optional
import os
import uuid

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://voice-auth-microservice.onrender.com/api/v1")

st.set_page_config(
    page_title="Voice Authentication Dashboard",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("public/authy.png", width=300)
    except:
        st.markdown('<h1 style="text-align: center;">🎤 Voice Authentication Dashboard</h1>', unsafe_allow_html=True)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
    }
    .success-alert {
        color: #155724;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .error-alert {
        color: #721c24;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def make_api_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make API request to voice authentication service"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-Call-ID": f"dashboard-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            error_data = response.json() if response.content else {"message": "Unknown error"}
            return {"success": False, "error": error_data}
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": {"message": f"Network error: {str(e)}"}}
    except Exception as e:
        return {"success": False, "error": {"message": f"Unexpected error: {str(e)}"}}

def check_service_health() -> Dict:
    """Check if the voice authentication service is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "unhealthy", "error": "Service unavailable"}
    except:
        return {"status": "unhealthy", "error": "Cannot connect to service"}

def enroll_user(user_id: str, phone: str, audio_url: str) -> Dict:
    """Enroll a user with voice authentication"""
    data = {
        "userId": user_id,
        "phone": phone,
        "audioUrl": audio_url
    }
    return make_api_request("/enroll-user", "POST", data)

def get_user_auth_history(phone: str, limit: int = 10) -> Dict:
    """Get authentication history for a user"""
    return make_api_request(f"/users/{phone}/auth-history?limit={limit}")

def main():
    # Header (logo already displayed above)
    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)  # Spacer
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "System Status",
        "User Enrollment", 
        "User Management",
        "Authentication History"
    ])
    
    # Check service health
    health_status = check_service_health()
    
    if health_status.get("status") == "healthy":
        st.sidebar.success("✅ Service Online")
    else:
        st.sidebar.error("❌ Service Offline")
        st.sidebar.text(health_status.get("error", "Unknown error"))
    
    # Page routing
    if page == "System Status":
        show_system_status(health_status)
    elif page == "User Enrollment":
        show_user_enrollment()
    elif page == "User Management":
        show_user_management()
    elif page == "Authentication History":
        show_auth_history()

def show_system_status(health_status: Dict):
    """Display system status page"""
    st.header("🔍 System Status")
    
    # Remove metrics, just show status as text
    overall_status = health_status.get("status", "unknown")
    st.write(f"Overall Status: {overall_status}")
    
    components = health_status.get("components", {})
    db_status = components.get("database", {}).get("status", "unknown")
    st.write(f"Database: {db_status}")
    ai_status = components.get("embedding_service", {}).get("status", "unknown")
    st.write(f"AI Model: {ai_status}")
    
    # Detailed status
    st.subheader("Detailed Information")
    if health_status.get("status") == "healthy":
        st.json(health_status)
    else:
        st.error(f"Service Error: {health_status.get('error', 'Unknown error')}")
    
    # Refresh button
    if st.button("🔄 Refresh Status"):
        st.rerun()

def show_user_enrollment():
    """Display user enrollment page"""
    st.header("👤 User Enrollment")
    
    st.markdown("""
https://voice-auth-microservice.onrender.com    **Instructions:**
    1. Generate or enter a unique User ID
    2. Enter the user's phone number in international format
    3. Provide a publicly accessible audio URL (WAV format recommended)
    4. Click "Enroll User" to process the voice enrollment
    """)
    
    # Enrollment form
    with st.form("enrollment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # User ID generation
            if st.form_submit_button("🎲 Generate New User ID"):
                new_user_id = str(uuid.uuid4())
                st.session_state.user_id = new_user_id
            
            user_id = st.text_input(
                "User ID (UUID format)",
                value=st.session_state.get("user_id", ""),
                placeholder="123e4567-e89b-12d3-a456-426614174000",
                help="Unique identifier for the user"
            )
            
            phone = st.text_input(
                "Phone Number",
                placeholder="+1234567890",
                help="Phone number in E.164 format (e.g., +1234567890)"
            )
        
        with col2:
            audio_url = st.text_input(
                "Audio URL",
                placeholder="https://example.com/voice-sample.wav",
                help="Publicly accessible URL to the user's voice sample"
            )
            
            # Audio format info
            st.info("""
            **Audio Requirements:**
            - Format: WAV, MP3, or M4A
            - Duration: 3-30 seconds
            - Quality: Clear speech, minimal background noise
            - Content: Natural speech (any language)
            """)
        
        submitted = st.form_submit_button("🎤 Enroll User", type="primary")
        
        if submitted:
            # Validate inputs
            if not user_id or not phone or not audio_url:
                st.error("❌ Please fill in all fields")
                return
            
            # Validate UUID format
            try:
                uuid.UUID(user_id)
            except ValueError:
                st.error("❌ Invalid User ID format. Please use UUID format.")
                return
            
            # Validate phone format
            if not phone.startswith('+') or len(phone) < 10:
                st.error("❌ Invalid phone format. Please use E.164 format (e.g., +1234567890)")
                return
            
            # Process enrollment
            with st.spinner("🎤 Processing voice enrollment..."):
                result = enroll_user(user_id, phone, audio_url)
                
                if result["success"]:
                    data = result["data"]
                    st.markdown(f"""
                    <div class="success-alert">
                        <strong>✅ Enrollment Successful!</strong><br>
                        Status: {data.get('status', 'enrolled')}<br>
                        Confidence Score: {data.get('score', 'N/A')}<br>
                        User ID: {user_id}<br>
                        Phone: {phone}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Clear form
                    if 'user_id' in st.session_state:
                        del st.session_state.user_id
                else:
                    error = result["error"]
                    st.markdown(f"""
                    <div class="error-alert">
                        <strong>❌ Enrollment Failed</strong><br>
                        Error: {error.get('error', 'Unknown error')}<br>
                        Message: {error.get('message', 'No details available')}<br>
                        Correlation ID: {error.get('correlation_id', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)

def show_user_management():
    """Display user management page"""
    st.header("👥 User Management")
    
    st.info("⚠️ This feature requires additional backend endpoints to list and manage users. Currently showing interface mockup.")
    
    # Mock user data for demonstration
    mock_users = [
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "phone": "+1234567890",
            "enrolled_at": "2024-01-15 10:30:00",
            "status": "enrolled",
            "verification_count": 5
        },
        {
            "user_id": "987fcdeb-51d3-43e7-b456-426614174001", 
            "phone": "+1987654321",
            "enrolled_at": "2024-01-14 15:45:00",
            "status": "enrolled",
            "verification_count": 2
        }
    ]
    
    # Search and filter
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("🔍 Search users", placeholder="Enter phone number or user ID")
    with col2:
        status_filter = st.selectbox("Filter by status", ["All", "enrolled", "pending", "disabled"])
    
    # Users table
    if mock_users:
        df = pd.DataFrame(mock_users)
        
        # Apply filters
        if search_term:
            df = df[df['user_id'].str.contains(search_term, case=False) | 
                   df['phone'].str.contains(search_term, case=False)]
        
        if status_filter != "All":
            df = df[df['status'] == status_filter]
        
        # Display table
        st.dataframe(
            df,
            column_config={
                "user_id": st.column_config.TextColumn("User ID", width="medium"),
                "phone": st.column_config.TextColumn("Phone", width="small"),
                "enrolled_at": st.column_config.DatetimeColumn("Enrolled At", width="medium"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "verification_count": st.column_config.NumberColumn("Verifications", width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No users found matching the criteria.")

def show_auth_history():
    """Display authentication history page"""
    st.header("📊 Authentication History")
    
    user_id = st.text_input(
        "Enter User ID to view history",
        placeholder="123e4567-e89b-12d3-a456-426614174000"
    )
    
    if st.button("📋 Get History") and user_id:
        with st.spinner("Loading authentication history..."):
            result = get_user_auth_history(user_id)
            
            if result["success"]:
                data = result["data"]
                attempts = data.get("attempts", [])
                
                if attempts:
                    st.success(f"✅ Found {len(attempts)} authentication attempts for user {user_id}")
                    
                    # Convert to DataFrame for better display
                    df = pd.DataFrame(attempts)
                    df['created_at'] = pd.to_datetime(df['created_at'])
                    df['success_icon'] = df['success'].apply(lambda x: '✅' if x else '❌')
                    
                    # Display as table
                    st.dataframe(
                        df,
                        column_config={
                            "id": st.column_config.NumberColumn("Attempt ID"),
                            "success_icon": st.column_config.TextColumn("Result", width="small"),
                            "score": st.column_config.NumberColumn("Score", format="%.3f"),
                            "created_at": st.column_config.DatetimeColumn("Timestamp")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        success_rate = (df['success'].sum() / len(df)) * 100
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    with col2:
                        avg_score = df[df['success']]['score'].mean()
                        st.metric("Avg Success Score", f"{avg_score:.3f}" if not pd.isna(avg_score) else "N/A")
                    with col3:
                        st.metric("Total Attempts", len(attempts))
                        
                else:
                    st.info("No authentication attempts found for this user.")
            else:
                error = result["error"]
                st.error(f"❌ Error: {error.get('message', 'Failed to fetch history')}")

if __name__ == "__main__":
    main()