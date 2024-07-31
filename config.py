import os
import logging
from chromadb.config import Settings
from rich.console import Console
from rich.padding import Padding

# load_dotenv()
ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

PERSIST_DIRECTORY = f"{ROOT_DIRECTORY}/assets/DB/cksall"

EMBEDDING_MODEL_NAME = "hkunlp/instructor-large"

OPENAI_MODEL="gpt-4o"

# Define the Chroma settings
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    is_persistent=True,
)

# logging config
logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s", level=logging.INFO
    )

console = Console()


# based on the prompt = hub.pull("hwchase17/structured-chat-agent")
SYSTEM_MESSAGE = '''You are a helpful, concise chatbot and kubernetes(k8s) expert for question-answering tasks. Respond to the human as helpfully and accurately as possible. You have access to the following tools:

{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, as shown:

```
{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

Follow this format:

Question: input question to answer
Thought: consider previous and subsequent steps
Action:
```
$JSON_BLOB
```
Observation: action result
... (repeat Thought/Action/Observation N times)
Thought: I know what to respond
Action:
```
{{
  "action": "Final Answer",
  "action_input": "Final response to human"
}}

Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation'''

HUMAN_MESSAGE = '''{input}

{agent_scratchpad}

(reminder to respond in a JSON blob no matter what)'''