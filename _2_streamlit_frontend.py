import streamlit as st
from _1_langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

#User message history should be in the session state as long as the browser session is active
#now this session state is a dictionary as we can save anything in it with the key name of our choice.
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

#loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#Since we are also maintaining history in the backend, we need to create a config and pass it
config = {'configurable':{'thread_id': 1}}

user_input = st.chat_input('Type here')

if user_input:

    #First add the message to message history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    #Now get the replies from the ai chatbot 
    response = chatbot.invoke({'messages': [HumanMessage(content= user_input)]}, config=config)
    ai_message = response['messages'][-1].content
    #Now add the assitant message also to the message history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    with st.chat_message('assistant'):
        st.text(ai_message)