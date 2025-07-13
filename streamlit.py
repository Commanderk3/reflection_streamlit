import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sentence_transformers import SentenceTransformer
from retriever import getContext
import config
import json
from utils.session_state import initialize_session_state
from utils.prompts import instructions, generate_algorithm
from utils.blocks import findBlockInfo
from utils.parser import convert_music_blocks

model = SentenceTransformer(
    config.EMBEDDING_MODEL,
    device='cpu',
    cache_folder='./model_cache'
)

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
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

algorithm = ""

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
    return reasoning_llm.invoke(summary_prompt)

def analysis(old_summary, new_summary):
    analysis_prompt = f"""
    You are an expert reflective coach analyzing a learner's journey. Your task is to deeply analyze these summaries to identify the following:

    1. Progress: What areas show clear signs of learning, growth, or improvement?
    2. Patterns: Are there recurring themes, ideas, challenges, or emotions?
    3. Gaps: What areas are underdeveloped or need further reflection or practice?
    4. Mindset: What does the learner's attitude toward learning suggest (e.g., confidence, curiosity, self-doubt)?
    5. Recommendations: Suggest 2-3 personalized next steps to deepen their learning or reflection.

    Present the analysis in clear sections with thoughtful insights.
    Avoid simply repeating what the summaries say — provide higher-level interpretation and reasoning.

    Previous Summary:
    {old_summary}
    Current Summary:
    {new_summary}
    Learning Outcome:
    """
    return reasoning_llm.invoke(analysis_prompt)

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
        st.session_state.messages[0] = SystemMessage(content=instructions[selected_mentor] + "\n\n--- Algorithm ---\n" + st.session_state.code_algorithm)
        # st.rerun()
        

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
    
    # Upload JSON file
    uploadFile = st.file_uploader("Choose a JSON file", type="json")
    if len(st.session_state.messages) > 1 and uploadFile is not None:
        try:
            st.session_state.uploaded = True
            data = json.load(uploadFile)
            st.success("Conversation updated!")
            st.json(data)
            
            st.session_state.mentor = data['mentor']
            
            for entry in data['msg_history']:
                if entry['role'] == 'System':
                    st.session_state.messages.insert(0, SystemMessage(content=entry['content']))
                elif entry['role'] == 'User':
                    st.session_state.messages.append(HumanMessage(content=entry['content']))
                else:
                    st.session_state.messages.append(AIMessage(content=entry['content']))
                    
        except Exception as e:
            st.error(f"Error reading JSON: {e}")


if 'data' not in st.session_state or not st.session_state.data :
    uploaded_data = st.text_area("Paste your MusicBlocks project data here:")
    if uploaded_data:
        st.session_state.data = uploaded_data
        st.success("Project data uploaded successfully!")
        
        data = json.loads(uploaded_data)
        
        flowchart = convert_music_blocks(data)
        blockInfo = findBlockInfo(flowchart)
        
        algorithm = llm.invoke(f"instructions:\n{generate_algorithm}\n\ncode:\n{flowchart}\n\nBlock Info:\n{blockInfo}")
        st.session_state.code_algorithm = algorithm.content   
        st.session_state.messages[0] = SystemMessage(content=instructions[selected_mentor] + "\n\n--- Algorithm ---\n" + algorithm.content)
        
        prompt = combined_input("", st.session_state.messages)
        response = stream_response(prompt, llm)
        st.session_state.messages.append(AIMessage(content=algorithm.content + response))
        st.rerun()

# Chat input
if st.session_state.uploaded or ('data' in st.session_state and st.session_state.data):
    if not st.session_state.terminated:
        if prompt := st.chat_input("What would you like to discuss about your MusicBlocks project?"):
            st.session_state.messages.append(HumanMessage(content=prompt))

            with st.spinner("Thinking..."):
                try:
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
        
# Display chat messages
for i, message in enumerate(st.session_state.messages):
    if not isinstance(message, SystemMessage):
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.write(message.content) 
    
with st.sidebar:
    # Download Button
    save_data = []
    for msg in st.session_state.messages:
        role = "System" if isinstance(msg, SystemMessage) else "User" if isinstance(msg, HumanMessage) else f"Assistant"
        save_data.append({"role": role, "content": msg.content})

    content = {
        "mentor": st.session_state.mentor,
        "msg_history": save_data
    }
    
    json_string = json.dumps(content, indent=4)
    
    st.download_button(
        label="Save Conversation",
        data=json_string,
        file_name="conversation.json",
        mime="application/json"
    )
    