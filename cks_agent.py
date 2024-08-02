import os, getpass
import click
from cks_core import cksCore

from config import (
    CHROMA_SETTINGS,
    EMBEDDING_MODEL_NAME,
    PERSIST_DIRECTORY,
    logging,
    console
)

@click.command()
@click.option(
    "-p", "--prompt", help="Initial prompt to start the conversation. (optional)"
)



def main(prompt):
    """
    Main function for the CLI.
    """
    logging.info(f"Starting CKS Agent... ")

    cksbot = cksCore()

    console.print("\n:robot: starting conversation with CKS agent ...", style="bold green")
    console.print("   type 'exit' to end the conversation.", style="italic")

    cksbot.chat()

if __name__ == '__main__':

    if not os.environ.get('OPENAI_API_KEY'):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("OpenAI API Key [sf-]:")

    """
    Disabling huggingface/tokenizers parallelism to avoid deadlocks...
    """
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    main()

"""
https://github.com/langchain-ai/langchain/issues/10460
2024-07-31 11:21:11,574 - WARNING - manager.py:293 - Error in RootListenersTracer.on_chain_end callback: ValueError()
2024-07-31 11:21:11,575 - WARNING - manager.py:335 - Error in callback coroutine: ValueError()
"""