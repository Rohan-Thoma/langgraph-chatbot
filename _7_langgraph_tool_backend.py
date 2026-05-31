from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.memory import InMemorySaver
#we disabled the inmemory saver and we will import sqlite saver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool 
from dotenv import load_dotenv
import sqlite3
import requests 
import os

load_dotenv()

# 1 . LLM
llm = ChatOpenAI()

# 2 Tools
#Tools
search_tool = DuckDuckGoSearchRun(region='us-en')

#Simple Calculator Tool
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """ 
    Perform a basic arithmetic operation on 2 numbers.
    Supported operations: add, sub, mul and div
    """

    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == 'div':
            if second_num == 0:
                return {'error': 'Division by zero is not allowed'}
            result = first_num / second_num
        else:
            return {"error" : {"Unsupported operation '{operation}'"}}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation,"result": result}
    except Exception as e:
        return {'error': str(e)}
    
#Tool for getting the stock price
@tool 
def get_stock_price(symbol:str) -> dict:
    """ 
    Fetch the latest stock price for a given symbol ( e.g. 'AAPL', 'TSLA')
    using Alpha Vantage with API key in the URL.
    """

    stock_api = os.getenv('ALPHA_VANTAGE_STOCK_API')
    
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={stock_api}"
    r = requests.get(url)
    return r.json()


#Add the tools to the LLM
tools = [get_stock_price, search_tool, calculator]

llm = ChatOpenAI()
llm_with_tools = llm.bind_tools(tools)

# 3. Define the state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# 4. Define the nodes
def chat_node(state: ChatState):
    """ 
    LLM node that may ansswer or request a tool call.
    """
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

# 5.Check pointer
#Lets create a database first to save all our chat data to it
#Here we need to keeep check_same_thread = False because it throws an error when we are trying to dave the database with multiple threads
conn = sqlite3.connect(database = 'chatbot.db', check_same_thread=False)

# Checkpointer
# checkpointer = InMemorySaver()
checkpointer = SqliteSaver(conn= conn)

# 6. graph
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

# 7. Helper
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