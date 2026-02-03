import asyncio
import sys
import time
import re
from urllib.parse import urlparse
import streamlit as st
from rag import process_urls, generate_answer

# Windows-specific event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# -------------------------------------------------
# Page Config
# -------------------------------------------------
st.set_page_config(
    page_title="Web-based RAG Assistant",
    page_icon="📖",
    layout="wide"
)

# -------------------------------------------------
# Logic: Professional Equation Rendering
# -------------------------------------------------
def render_assistant_response(raw_text):
    # Fix common artifacts
    raw_text = raw_text.replace(r"{\rm", r"\text{").replace(r"{\displaystyle", "").replace(r"d{k}", r"d_k")
    
    lines = raw_text.split('\n')
    for line in lines:
        if not line.strip(): continue
            
        # Check if line is an equation
        if any(char in line for char in ['\\', ':=', '^T', '_{', 'softmax', 'exp']):
            clean_math = line.replace('$', '').strip()
            # Basic balancing for scraped Wikipedia braces
            if clean_math.count('{') < clean_math.count('}'):
                clean_math = clean_math.rstrip('}')
            st.latex(clean_math)
        else:
            st.markdown(line)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def is_valid_url(url: str) -> bool:
    try:
        url = url.strip()
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

# -------------------------------------------------
# Session State
# -------------------------------------------------
if "urls_processed" not in st.session_state:
    st.session_state.urls_processed = False
if "last_urls" not in st.session_state:
    st.session_state.last_urls = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.title("⚙️ Knowledge Setup")
    url1 = st.text_input("URL 1", placeholder="https://...")
    url2 = st.text_input("URL 2", placeholder="https://...")
    url3 = st.text_input("URL 3", placeholder="https://...")

    raw_urls = [u.strip() for u in (url1, url2, url3) if u.strip()]
    valid_urls = [u for u in raw_urls if is_valid_url(u)]

    if valid_urls != st.session_state.last_urls:
        st.session_state.urls_processed = False

    st.markdown("---")
    
    if st.button("Process URLs", type="primary", use_container_width=True):
        if not valid_urls:
            st.error("❌ Please enter valid URLs.")
        else:
            st.session_state.last_urls = valid_urls
            status_box = st.empty()
            progress_bar = st.progress(0)
            
            # FIX: Use a local variable for progress
            current_pct = 0
            
            try:
                for step in process_urls(valid_urls):
                    status_box.info(f"📋 {step}")
                    current_pct = min(95, current_pct + 20)
                    progress_bar.progress(current_pct)
                
                progress_bar.progress(100)
                st.session_state.urls_processed = True
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("Reset App", use_container_width=True):
        st.session_state.urls_processed = False
        st.session_state.last_urls = []
        st.session_state.messages = []
        st.rerun()

# -------------------------------------------------
# Main Chat
# -------------------------------------------------
st.title("📖 Web-based RAG Assistant")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_assistant_response(message["content"])
        else:
            st.markdown(message["content"])

if not st.session_state.urls_processed:
    st.info("👈 **Setup your sources in the sidebar to begin.**")
else:
    if query := st.chat_input("Ask about the papers..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Analyzing..."):
                    raw_answer, sources = generate_answer(query)
                    render_assistant_response(raw_answer)
                    
                    if sources:
                        with st.expander("📚 Sources"):
                            for src in sources:
                                st.write(f"- {src}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": raw_answer})
            except Exception as e:
                st.error(f"❌ Error: {e}")
