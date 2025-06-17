import streamlit as st
from langchain_core.messages import SystemMessage
from utils.prompts import instructions

def initialize_session_state():
    if "mentor" not in st.session_state:
        st.session_state.mentor = "meta"
    if "messages" not in st.session_state:
        st.session_state.messages = [SystemMessage(content=instructions[st.session_state.mentor])]
    if "terminated" not in st.session_state:
        st.session_state.terminated = False
    if "summary" not in st.session_state:
        st.session_state.summary = ""
    if "analysis" not in st.session_state:
        st.session_state.analysis = ""
    if "old_summary" not in st.session_state:
        st.session_state.old_summary = """
    Let's summarize what we've discussed so far:
    You created a project in Music Blocks and made a cool hip-hop beat. You used the Pitch-Drum Matrix to experiment with different rhythms and patterns, which allowed you to think freely and focus on the creative aspect.
    You learned that trying different patterns is not the only thing to focus on when creating a beat, and that splitting a note value can lead to some really cool and unique sounds.
    You're planning to create a chord progression that suits your beat and wants to enhance or complement its vibe.
    """

