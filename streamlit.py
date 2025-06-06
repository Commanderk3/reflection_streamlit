import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
import config

model = SentenceTransformer(
    config.EMBEDDING_MODEL,
    device='cpu',
    cache_folder='./model_cache'
)

# Initialize all components directly
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0.7
)

# Initialize vector store
embeddings = HuggingFaceEmbeddings(
    model_name=config.EMBEDDING_MODEL,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': False}
)
qdrant_client = QdrantClient(
    url=config.QDRANT_URL,
    api_key=config.QDRANT_API_KEY,
)
vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name="mb_docs",
    embedding=embeddings
)
relevance_threshold = 0.3

def getContext(query):
    results = vectorstore.similarity_search_with_score(query, k=3)
    relevant_docs = [(doc, score) for doc, score in results if score > relevance_threshold]
    print("Scores:", [score for _, score in results])
    if relevant_docs:
        rag_context = " ".join(doc.page_content for doc, _ in relevant_docs)
        return rag_context
    return None

# Instruction prompt
instruction = """
Role: You are a teacher on the MusicBlocks platform, guiding users through deep, analytical discussions that foster conceptual learning and self-improvement. WORD LIMIT: 30.
Guidelines:
1.Structured Inquiry: Ask these in order:
    What did you do?,
    Why did you do it?,
    What approach you used? Why this approach?,
    Ask technical questions based on context. Discuss alternatives. (Ask follow-up questions),
    Were you able to achieve the desired goal? If no, what do you think went wrong? (Ask follow-up questions to clarify),
    What challenges did you face?,
    What did you learn?,
    What's next?

2.Cross question if something is not clear,
3.Try to get to the root of the user's understanding,
4.Avoid repetition. Adapt questions based on context and previous responses.
5.Judge the provided context, if it has context to user query then use it.
6.Keep the conversation on track if the user deviates.
7.Limit your side to 20 dialogues.
8.Focus only on the current project. Ignore past projects.
9.After all questions, ask if they want to continue. If not, give a goodbye message.
"""

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [SystemMessage(content=instruction)]
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

# Helper functions
def combined_input(rag, messages):
    conversation_history = ""
    for msg in messages:
        role = "System" if isinstance(msg, SystemMessage) else "User" if isinstance(msg, HumanMessage) else "Assistant"
        conversation_history += f"{role}: {msg.content}\n"
    return f"Context: {rag}\nConversation History:\n{conversation_history}\nAssistant:"

def generate_summary(messages):
    user_queries = [msg.content for msg in messages if isinstance(msg, HumanMessage)]
    assistant_responses = [msg.content for msg in messages if isinstance(msg, AIMessage)]
    summary_prompt = f"""
    Analyze the following conversation and generate a concise summary for the User's learning and takeaways points. Cover User Queries only.
    Add only relevant information in this summary. Write a paragraph under 100 words (detailed).
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

# Page setup
st.title("Reflective Learning")
st.caption("A conversational guide for your MusicBlocks learning journey")

# Sidebar for additional features
with st.sidebar:
    st.header("Additional Options")

    # Generate Summary Button
    if st.button("Generate Summary"):
        try:
            new_summary = generate_summary(st.session_state.messages)
            st.session_state.summary = new_summary.content

            st.session_state.messages.append(
                AIMessage(content=f"📝 Here's a summary of our conversation:\n\n{new_summary.content}")
            )
            
            # Display the new message
            with st.chat_message("assistant"):
                st.markdown(f"📝 Here's a summary of our conversation:\n\n{new_summary.content}")
                
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")

    # Generate Analysis Button (only if summary is generated)
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
                
                # Display the new message
                with st.chat_message("assistant"):
                    st.markdown(f"📈 Learning Outcome:\n\n{outcome.content}")
                    
            except Exception as e:
                st.error(f"Error generating analysis: {str(e)}")

# Display chat messages
for message in st.session_state.messages:
    if isinstance(message, SystemMessage):
        continue  # Skip system messages in display
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

# Chat input
if not st.session_state.terminated:
    if prompt := st.chat_input("What would you like to discuss about your MusicBlocks project?"):
        # Add user message to history and display
        user_message = HumanMessage(content=prompt)
        st.session_state.messages.append(user_message)
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.spinner("Thinking..."):
            try:
                # Get relevant context from vector store
                relevant_docs = getContext(prompt)
                
                # Generate response
                prompt_with_context = combined_input(relevant_docs, st.session_state.messages)
                result = llm.invoke(prompt_with_context)
                full_response = result.content
                
                # Add to messages and display
                assistant_message = AIMessage(content=full_response)
                st.session_state.messages.append(assistant_message)
                with st.chat_message("assistant"):
                    st.markdown(full_response)

                # Check if conversation should terminate
                if len([m for m in st.session_state.messages if isinstance(m, AIMessage)]) > 20:
                    if decide_to_terminate(full_response) == "yes":
                        st.session_state.terminated = True
                        st.rerun()

            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                st.session_state.messages.append(
                    AIMessage(content="Sorry, I'm having trouble generating a response. Please try again.")
                )
else:
    st.info("This conversation has ended. Please refresh the page to start a new one.")