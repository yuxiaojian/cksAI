import os
from rich.padding import Padding
from rich.markdown import Markdown
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceInstructEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

import subprocess
from rich.padding import Padding
import prompt_toolkit
#from prompt_toolkit.styles import Style

from tool_handler import registry
from config import (
    CHROMA_SETTINGS,
    EMBEDDING_MODEL_NAME,
    PERSIST_DIRECTORY,
    OPENAI_MODEL,
    SYSTEM_MESSAGE,
    HUMAN_MESSAGE,
    logging,
    console
)

class ProposeK8sCommandSchema(BaseModel):
    """
    Suggest kubectl command input.
    """

    notes: str = Field(
        description="A short docstring about the command"
    )
    query: str = Field(
        description="A kubectl command that the user can run."
    )

def k8s_command_run(notes: str, query: str) -> str:
    """Wait for user confirmation and run the command."""
    if notes:
            console.print("\nNote: " + notes + "\n", style="italic")
    if query:
        cmd = prompt_toolkit.prompt(
            "Edit the cmd and press (enter) to run, leave empty to return \n\n",
            default=query,
        )
    args = cmd.split()

    # Check if any command is entered, then run it
    output=''
    if args:
        console.print("\n")
        try:
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            console.print(output)
        except Exception as e:
            output = str(e)
    else:
        console.print("No command entered.")

    return f"[ProposeK8sCommand]{output}||{cmd}"



def get_all_tools(retriever):
    """
    Get all tools.
    """
    retriever_tool = create_retriever_tool(
        retriever,
        "cks_allowed_docs_search",
        "Search for information from allowed documentation in CKS test, including K8s, falco, trivy, etcd and apparmor.",
    )

    ProposeK8sCommandTool = StructuredTool.from_function(
        func=k8s_command_run,
        name="ProposeK8sCommand",

        description = "Propose a kubectl command in the terminal. \
            The user can either directly execute the command or modify and then run the command.\
            execute the command directly. They will be able to edit it before executing.\
            The command should be properly formatted and can include placeholders for the user to fill in. \
            if it answer's the user's question or solves their errors. If the user's question is more general, you should use the `k8s_search` \
            tool instead or answer the question directly.",
        args_schema=ProposeK8sCommandSchema,
        return_direct=True,
        # coroutine= ... <- you can specify an async method if desired as well
    )

    tools = [retriever_tool, ProposeK8sCommandTool]

    return tools

def create_bot(retriever, llm):
    """
    Create a bot with tools.
    """
    tools = get_all_tools(retriever)

    prompt_custom = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", HUMAN_MESSAGE),
        ]
    )

    agent = create_structured_chat_agent(llm, tools, prompt_custom)
    
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)

    memory = ChatMessageHistory(session_id="abc123")
    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        lambda session_id: memory,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    return agent_with_chat_history


class cksCore:
    """
    cksCore is the RAG app to interact with LLM
    """
    def __init__(self):
        logging.info(f"Loading embeddings from %s" %(PERSIST_DIRECTORY))

        embeddings = HuggingFaceInstructEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            embed_instruction="Represent the document for retrieval:",
            query_instruction="Represent the question for retrieving supporting documents:",
        )

        vectordb = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings,
            client_settings=CHROMA_SETTINGS
        )

        logging.info("There are %d in the collection" % vectordb._collection.count())
        # Check if the vector database is empty and log a warning if so
        if len(vectordb.get(limit=1).get("documents", [])) == 0:
            logging.warning("The vector database is empty.")

        self.retriever =  vectordb.as_retriever(
            search_type="mmr",  # Also test "similarity"
            search_kwargs={"k": 2},
        )
        self.llm = ChatOpenAI(temperature=0, model=OPENAI_MODEL)
        self.bot = create_bot(self.retriever, self.llm)

    def chat( self):
        """
        Start a chat with the bot. User can end with 'exit'.
        """
        additional_context = None
        while True:
            user_prompt = input("Prompt: ")
            if user_prompt.lower() == "exit":
                break

            for chunk in self.bot.stream(
                {"input": user_prompt},
                config={"configurable": {"session_id": "abc123"}},
            ):
                # Agent Action
                if "actions" in chunk:
                    for action in chunk["actions"]:
                        console.print(
                            Padding(
                                f":hammer: Calling Tool: `{action.tool}` with input `{action.tool_input}`",
                                pad=(0, 0, 0, 2),
                            ),
                            style="italic bright_black",
                        )
                # Observation
                elif "steps" in chunk:
                    continue
                # Final result
                elif "output" in chunk:
                    if registry.has_tool_handler(chunk["output"]):
                        additional_context = registry.use_handler(
                            chunk["output"]
                        )
                    else:
                        console.print("cksagent:\n", style="bold green")
                        console.print(Markdown(chunk["output"]))
                else:
                    raise ValueError()
                console.print("---")

