from langgraph.graph import StateGraph, START 
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool 
import asyncio

#This is needed to create mcp clients in langgraph
from langchain_mcp_adapters.client import MultiServerMCPClient
load_dotenv()

# 1 . LLM
llm = ChatOpenAI()

#define tool via mcp server
#MCP client for a local mcp server
#now the tools are all inside the server, which this client will call
client = MultiServerMCPClient(
    {
        "math_operations":{
            "transport": "stdio",
            "command": "/home/dragon/.virtualenvs/mcp-campusx/bin/python",
            "args": ["/home/dragon/GEN-AI Udemy/MCP-Campus-X/Expense-Tracker-MCP/Math_operations_server.py"]
        },
        'expense_tracker': {
            "transport": "streamable_http",
            "url": "https://expense-tracker-remote-corrected.fastmcp.app/mcp"
        }
    }
)

#Now lets create the graph
#first define the state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage],add_messages]

#Lets build the graph inside a function now
async def build_graph():

    #Client will get the list of tools presenti inside the server
    tools = await client.get_tools()
    print("Tools = ", tools)
    
    #now give llm access to the tools that we have got from the mcp server
    llm_with_tools = llm.bind_tools(tools)

    #define the nodes but in async fashion
    async def chat_node(state: ChatState):

        messages = state['messages']
        response = await llm_with_tools.ainvoke(messages)
        return {'messages': [response]}
    
    #This toolnode is internally asynchronous , so no need to make it also async
    tool_node = ToolNode(tools) 

    #Defining graph and nodes
    graph = StateGraph(ChatState)

    graph.add_node('chat_node', chat_node)
    graph.add_node('tools', tool_node)

    #Defining graph connections
    graph.add_edge(START, 'chat_node')
    graph.add_conditional_edges('chat_node', tools_condition)
    graph.add_edge('tools', 'chat_node')

    #Now compile the graph    
    chatbot = graph.compile()

    return chatbot


async def main():

    #build graph is async to we need to use await here also
    chatbot = await build_graph()

    #running the graph
    result = await chatbot.ainvoke(
        {"messages": [HumanMessage(content="Find the modulus of 1223232 and 23 and give the answer like a basketball commentator.")]}
    )

    print(result['messages'][-1].content)

if __name__ == "__main__":
   asyncio.run(main()) 