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
