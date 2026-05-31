import streamlit as st
from _6_langgraph_database_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage
import uuid

#******************************** Utility Functions ********************************

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    return chatbot.get_state(
        config = {'configurable': {'thread_id': thread_id}}
    ).values.get('messages', [])

#******************************** Session Setup *********************************

#User message history should be in the session state as long as the browser session is active
#now this session state is a dictionary as we can save anything in it with the key name of our choice.
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

add_thread(st.session_state['thread_id'])

#***************************** Side Bar UI *************************************

st.sidebar.title('Langgraph Chatbot')

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header('My conversations')

for thread_id in st.session_state['chat_threads'][::-1]: 
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        #To bring the langraph messages object format to the normal format which we are using , we need to do some manual format tweaking
        temp_messages = []
        for message in messages:

            if isinstance(message, HumanMessage):
                role = 'user'
            else:
                role = 'assistant'

            temp_messages.append({'role': role, 'content': message.content})

        st.session_state['message_history'] = temp_messages

#loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#Since we are also maintaining history in the backend, we need to create a config and pass it
# config = {'configurable':{'thread_id': st.session_state['thread_id']}}

#This metadata insertion is additional thing for naming the threads creates in the chatbot to be able to recognized in langsmith tracking
config = {'configurable':{'thread_id': st.session_state['thread_id']},
          'meta_data':{
              "thread_id": st.session_state['thread_id']
          },
          'run_name': 'chat_turn'}

user_input = st.chat_input('Type here')

if user_input:

    #First add the message to message history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    #Now get the replies from the ai chatbot via streaming also we need to show the streaming in frontend also.
    with st.chat_message('assistant'):
        #Now this streamlit stream function requires a generator object, which we will get from langraph
        #Instead of invoke(), we need to call stream() function of the graph object
        ai_message = st.write_stream(
            message_chunk.content for message_chunk,metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config= config,
                stream_mode= 'messages'
            )
        )
    
    #Now add the assitant message also to the message history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    