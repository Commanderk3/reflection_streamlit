import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from retriever import getContext
import config
from utils.session_state import initialize_session_state
from utils.prompts import instructions, generate_algorithm
from utils.blocks import findBlockInfo

model = SentenceTransformer(
    config.EMBEDDING_MODEL,
    device='cpu',
    cache_folder='./model_cache'
)

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0.7,
    disable_streaming=False
)

reasoning_llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0.7,
    disable_streaming=False
)

# Initialize session state
initialize_session_state()

def combined_input(rag, messages):
    conversation_history = ""
    for msg in messages:
        role = "System" if isinstance(msg, SystemMessage) else "User" if isinstance(msg, HumanMessage) else f"{selected_mentor} assistant"
        conversation_history += f"{role}: {msg.content}\n"
        final_prompt = f"Conversation History:\n{conversation_history}" + f"\n\nContext: {rag}\n\n{selected_mentor} assistant:"
    return final_prompt

def generate_summary(messages):
    user_queries = [msg.content for msg in messages if isinstance(msg, HumanMessage)]
    assistant_responses = [msg.content for msg in messages if isinstance(msg, AIMessage)]
    summary_prompt = f"""
    Analyze the following conversation and generate a concise summary for the User's learning and takeaways points. Cover User Queries only.
    Add only relevant information in this summary. Write a paragraph under 200 words (detailed).
    User Queries:
    {user_queries}
    Assistant Responses:
    {assistant_responses}
    Summary:
    """
    return llm.invoke(summary_prompt)

def analysis(old_summary, new_summary):
    analysis_prompt = f"""
    Analyze the user's learning by comparing two summaries. Identify key improvements, knowledge growth, and remaining gaps. 
    Provide a constructive, truthful and realistic assessment of their development over time in a paragraph under 50 words, avoiding flattery.
    Previous Summary:
    {old_summary}
    Current Summary:
    {new_summary}
    Learning Outcome:
    """
    return llm.invoke(analysis_prompt)

def decide_to_terminate(response):
    prompt = f"""
    AI Message: "{response}"
    Did the AI say bye to the user? Is the AI saying that the conversation is over and come to an end? 
    (only yes/no)
    """
    decision = llm.invoke(prompt).content.strip().lower()
    return decision

def stream_response(prompt, model):
    full_response = ""  
    container = st.empty()        
    for chunk in model.stream([HumanMessage(content=prompt)]):
        full_response += chunk.content
        container.markdown(full_response + "▌")                           
    container.markdown(full_response)
    
    return full_response


st.title("Reflective Learning")
st.caption("A conversational guide for your MusicBlocks learning journey")

# Sidebar for additional features
with st.sidebar:
    st.header("Additional Options")

    selected_mentor = st.selectbox(
        "Choose a Mentor", 
        options=["meta", "music", "code"], 
        index=["meta", "music", "code"].index(st.session_state.mentor)
    )
    if selected_mentor != st.session_state.mentor:
        st.session_state.mentor = selected_mentor
        if selected_mentor != st.session_state.mentor:
            st.session_state.mentor = selected_mentor
            
        for idx, msg in enumerate(st.session_state.messages):
            if isinstance(msg, SystemMessage):
                st.session_state.messages[idx] = SystemMessage(content=instructions[selected_mentor])
                break
        else:
            st.session_state.messages.insert(0, SystemMessage(content=instructions[selected_mentor]))
            # st.rerun()
        
    if st.button("Generate Summary"):
        try:
            if len(st.session_state.messages) < 10:
                st.warning("⚠️ Not enough messages to generate a summary. Please have a conversation first.")
            else:
                new_summary = generate_summary(st.session_state.messages)
                st.session_state.summary = new_summary.content
                st.session_state.messages.append(
                    AIMessage(content=f"📝 Here's a summary of our conversation:\n\n{new_summary.content}")
                )
                
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")

    if st.button("Generate Analysis"):
        if not st.session_state.summary:
            st.warning("⚠️ Please generate a summary first.")
        else:
            try:
                outcome = analysis(st.session_state.old_summary, st.session_state.summary)
                st.session_state.outcome = outcome.content
                st.session_state.messages.append(
                    AIMessage(content=f"📈 Learning Outcome:\n\n{outcome.content}")
                )
                    
            except Exception as e:
                st.error(f"Error generating analysis: {str(e)}")


# Display chat messages
for message in st.session_state.messages:
    if isinstance(message, SystemMessage):
        continue
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

# Chat input
if not st.session_state.terminated:
    if prompt := st.chat_input("What would you like to discuss about your MusicBlocks project?"):

        user_message = HumanMessage(content=prompt)
        st.session_state.messages.append(user_message)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            try:
                startBlock = "Start of Project\n├──"
                if startBlock in prompt:
                    blockInfo = findBlockInfo(prompt)
                    algorithm = stream_response(f"instructions:\n{generate_algorithm}\n\ncode:\n{prompt}\n\nBlock Info:\n{blockInfo}", reasoning_llm)
                    st.session_state.messages.append(AIMessage(content=algorithm))
    
                else : 
                    relevant_docs = getContext(prompt)
                    prompt_with_context = combined_input(relevant_docs, st.session_state.messages)
                    response = stream_response(prompt_with_context, llm)               
                    st.session_state.messages.append(AIMessage(content=response))

            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                st.session_state.messages.append(
                    AIMessage(content="Sorry, I'm having trouble generating a response. Please try again.")
                )
else:
    st.info("This conversation has ended. Please refresh the page to start a new one.")