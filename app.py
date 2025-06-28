import streamlit as st
import requests
import json
from datetime import datetime
import threading
import subprocess
import time
import sys
import os

# Start FastAPI backend if not already running
@st.cache_resource
def start_backend():
    """Start the FastAPI backend server"""
    try:
        # Check if backend is already running
        response = requests.get("http://localhost:8000/health", timeout=1)
        if response.status_code == 200:
            return True
    except:
        pass
    
    # Start backend in a separate process
    def run_backend():
        subprocess.run([sys.executable, "backend.py"], cwd=os.getcwd())
    
    thread = threading.Thread(target=run_backend, daemon=True)
    thread.start()
    
    # Wait for backend to start
    for _ in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            time.sleep(1)
    
    return False

def main():
    st.set_page_config(
        page_title="AI Booking Assistant",
        page_icon="📅",
        layout="wide"
    )
    
    # Create tabs for main app and setup
    tab1, tab2 = st.tabs(["💬 Chat Assistant", "⚙️ Calendar Setup"])
    
    with tab1:
        st.title("🗓️ AI Booking Assistant")
        st.markdown("Schedule appointments naturally with our AI assistant")
        
        # Start backend
        backend_started = start_backend()
        if not backend_started:
            st.error("Failed to start backend service. Please try refreshing the page.")
            return
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
            st.session_state.conversation_id = None
        
        render_chat_interface()
    
    with tab2:
        render_calendar_setup()

def render_chat_interface():
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your booking request here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/chat",
                        json={
                            "message": prompt,
                            "conversation_id": st.session_state.conversation_id
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        assistant_message = data["response"]
                        st.session_state.conversation_id = data["conversation_id"]
                        
                        st.markdown(assistant_message)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": assistant_message
                        })
                    else:
                        error_msg = "Sorry, I encountered an error. Please try again."
                        st.markdown(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": error_msg
                        })
                        
                except requests.exceptions.RequestException as e:
                    error_msg = "Sorry, I'm having trouble connecting. Please try again."
                    st.markdown(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

def render_calendar_setup():
    st.title("📅 Calendar Setup")
    st.markdown("Connect your Google Calendar to enable real appointment booking")
    
    # Check current status
    import os
    has_service_account = os.path.exists('credentials.json')
    has_oauth_secrets = os.path.exists('client_secrets.json')
    has_oauth_token = os.path.exists('token.json')
    
    # Status indicators
    st.subheader("📊 Current Status")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if has_service_account:
            st.success("✅ Service Account Found")
        else:
            st.info("❌ No Service Account")
    
    with col2:
        if has_oauth_secrets:
            st.success("✅ OAuth Secrets Found")
        else:
            st.info("❌ No OAuth Secrets")
    
    with col3:
        if has_oauth_token:
            st.success("✅ OAuth Token Found")
        else:
            st.info("❌ No OAuth Token")
    
    # Integration status
    if has_service_account or (has_oauth_secrets and has_oauth_token):
        st.success("🎉 Google Calendar is ready to use!")
        st.markdown("Your booking assistant can now create real calendar events.")
    elif has_oauth_secrets:
        st.warning("⚠️ OAuth setup started but not complete")
        st.markdown("The first booking request will open a browser for authentication.")
    else:
        st.error("❌ Google Calendar not connected")
        st.markdown("Currently using demonstration mode only.")
    
    # Setup instructions
    st.subheader("🔧 Setup Instructions")
    
    setup_option = st.radio(
        "Choose your setup method:",
        ["OAuth2 (Recommended for personal use)", "Service Account (For shared/production use)"]
    )
    
    if setup_option == "OAuth2 (Recommended for personal use)":
        st.markdown("""
        ### OAuth2 Setup (Quick & Easy)
        
        1. **Go to Google Cloud Console**
           - Visit [console.cloud.google.com](https://console.cloud.google.com)
           - Create a new project or select existing one
        
        2. **Enable Calendar API**
           - Go to "APIs & Services" → "Library"
           - Search for "Google Calendar API"
           - Click "Enable"
        
        3. **Create OAuth2 Credentials**
           - Go to "APIs & Services" → "Credentials"
           - Click "Create Credentials" → "OAuth client ID"
           - Configure consent screen if prompted (choose "External")
           - Select "Desktop application"
           - Name it "AI Booking Assistant"
           - Click "Create"
        
        4. **Download and Upload**
           - Download the JSON credentials file
           - Upload it here with the exact name `client_secrets.json`
        """)
        
        uploaded_file = st.file_uploader(
            "Upload your client_secrets.json file:",
            type=['json'],
            help="This file contains your OAuth2 credentials from Google Cloud Console"
        )
        
        if uploaded_file is not None:
            try:
                import json
                content = json.loads(uploaded_file.getvalue().decode("utf-8"))
                
                # Validate it's an OAuth2 client secrets file
                if "installed" in content or "web" in content:
                    with open("client_secrets.json", "w") as f:
                        f.write(uploaded_file.getvalue().decode("utf-8"))
                    st.success("✅ OAuth2 credentials saved successfully!")
                    st.info("💡 When you make your first booking request, a browser window will open for authentication.")
                    st.experimental_rerun()
                else:
                    st.error("❌ Invalid OAuth2 credentials file. Please check the file format.")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file. Please upload a valid credentials file.")
    
    else:  # Service Account
        st.markdown("""
        ### Service Account Setup (Advanced)
        
        1. **Create Service Account**
           - Go to "IAM & Admin" → "Service Accounts"
           - Click "Create Service Account"
           - Name: `ai-booking-assistant`
           - Create and download JSON key file
        
        2. **Share Calendar**
           - Find service account email in the JSON file
           - Share your Google Calendar with this email
           - Grant "Make changes to events" permission
        
        3. **Upload Credentials**
           - Upload the service account JSON file as `credentials.json`
        """)
        
        uploaded_file = st.file_uploader(
            "Upload your credentials.json file:",
            type=['json'],
            help="This file contains your service account credentials"
        )
        
        if uploaded_file is not None:
            try:
                import json
                content = json.loads(uploaded_file.getvalue().decode("utf-8"))
                
                # Validate it's a service account file
                if "type" in content and content["type"] == "service_account":
                    with open("credentials.json", "w") as f:
                        f.write(uploaded_file.getvalue().decode("utf-8"))
                    st.success("✅ Service account credentials saved!")
                    
                    # Show service account email for calendar sharing
                    service_email = content.get("client_email", "Unknown")
                    st.info(f"📧 Share your calendar with: `{service_email}`")
                    st.experimental_rerun()
                else:
                    st.error("❌ Invalid service account file. Please check the file format.")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file. Please upload a valid credentials file.")
    
    # Test connection button
    if has_service_account or has_oauth_secrets:
        st.subheader("🧪 Test Connection")
        if st.button("Test Google Calendar Connection"):
            with st.spinner("Testing connection..."):
                try:
                    response = requests.get("http://localhost:8000/health")
                    if response.status_code == 200:
                        st.success("✅ Backend is running")
                        
                        # Try to get availability (this will test calendar connection)
                        from datetime import datetime, timedelta
                        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                        day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                        
                        response = requests.get(
                            f"http://localhost:8000/availability?start_date={tomorrow}&end_date={day_after}"
                        )
                        
                        if response.status_code == 200:
                            st.success("✅ Google Calendar connection working!")
                        else:
                            st.error("❌ Calendar connection failed. Check your credentials.")
                    else:
                        st.error("❌ Backend service not responding")
                except Exception as e:
                    st.error(f"❌ Connection test failed: {str(e)}")
    
    # Sidebar with helpful information and data views
    with st.sidebar:
        st.header("💡 Tips")
        st.markdown("""
        **Try saying:**
        - "I need to book a meeting tomorrow at 2 PM"
        - "Do you have any free time this Friday?"
        - "Schedule a call for next week between 3-5 PM"
        - "What's available on Monday morning?"
        
        **Features:**
        - ✅ Natural language understanding
        - ✅ Google Calendar integration
        - ✅ Smart availability checking
        - ✅ Automatic booking confirmation
        - ✅ Database storage for history
        
        **Setup Google Calendar:**
        See `GOOGLE_CALENDAR_SETUP.md` for integration instructions
        """)
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()
        
        # Data views section
        st.divider()
        st.header("📊 Data Views")
        
        # Recent conversations
        if st.button("View Recent Conversations"):
            try:
                response = requests.get("http://localhost:8000/conversations", timeout=5)
                if response.status_code == 200:
                    conversations = response.json()["conversations"]
                    st.subheader("Recent Conversations")
                    for conv in conversations[:5]:
                        st.write(f"**ID:** {conv['id'][:8]}...")
                        st.write(f"**Messages:** {conv['message_count']}")
                        st.write(f"**Created:** {conv['created_at'][:10]}")
                        if conv['last_message']:
                            st.write(f"**Last:** {conv['last_message'][:50]}...")
                        st.write("---")
                else:
                    st.error("Could not load conversations")
            except:
                st.error("Backend not available")
        
        # Recent bookings
        if st.button("View Recent Bookings"):
            try:
                response = requests.get("http://localhost:8000/bookings", timeout=5)
                if response.status_code == 200:
                    bookings = response.json()["bookings"]
                    st.subheader("Recent Bookings")
                    for booking in bookings[:5]:
                        st.write(f"**Title:** {booking['title']}")
                        st.write(f"**Date:** {booking['start_time'][:10]}")
                        st.write(f"**Time:** {booking['start_time'][11:16]}")
                        st.write(f"**Status:** {booking['status']}")
                        st.write("---")
                else:
                    st.error("Could not load bookings")
            except:
                st.error("Backend not available")

if __name__ == "__main__":
    main()
