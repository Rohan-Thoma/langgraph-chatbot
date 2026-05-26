from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.memory import InMemorySaver
#we disabled the inmemory saver and we will import sqlite saver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

load_dotenv()

llm = ChatOpenAI()

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}


#Lets create a database first to save all our chat data to it
#Here we need to keeep check_same_thread = False because it throws an error when we are trying to dave the database with multiple threads
conn = sqlite3.connect(database = 'chatbot.db', check_same_thread=False)

# Checkpointer
# checkpointer = InMemorySaver()
checkpointer = SqliteSaver(conn= conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

#Lets define a utility function which gets all the thread-ids present in the database
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    
    return list(all_threads)

#Lets write a small test 
if __name__ == "__main__":
    CONFIG = {'configurable': {'thread_id': "thread-1"}}

    #here we will first run this, now it should get saved to the database with the same thread-id
    # response = chatbot.invoke(
    #     {'messages': [HumanMessage(content='Hi my name is dragon')]},
    #     config = CONFIG
    # )

    #Now that above code is run, lets comment that out and ask what is my name
    response = chatbot.invoke(
        {'messages': [HumanMessage(content='What is my name?')]},
        config = CONFIG
    )
    print(response)