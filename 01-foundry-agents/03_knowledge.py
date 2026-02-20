"""
03 — Adding Knowledge (File Search and Vector Stores)

Uploads a document (audit standards reference) to Azure AI Foundry, creates
a vector store for retrieval, and attaches it to an agent via the
FileSearchTool so the agent can ground its answers in the document.

Concepts: file upload, vector stores, FileSearchTool, grounded responses
"""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, FilePurpose
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    client = AIProjectClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

    # Upload a knowledge document
    data_path = os.path.join(SCRIPT_DIR, "data", "sample_audit_standards.md")
    file = client.agents.upload_file_and_poll(
        file_path=data_path,
        purpose=FilePurpose.AGENTS,
    )
    print(f"Uploaded file: {file.id}")

    # Create a vector store from the uploaded file
    vector_store = client.agents.create_vector_store_and_poll(
        file_ids=[file.id],
        name="audit-standards-kb",
    )
    print(f"Created vector store: {vector_store.id}")

    # Create an agent with file search grounding
    agent = client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="KnowledgeAgent",
        instructions=(
            "You are an audit standards expert. Use the attached knowledge base "
            "to answer questions. Always cite the specific standard when possible."
        ),
        tools=FileSearchTool(vector_store_ids=[vector_store.id]).definitions,
        tool_resources=FileSearchTool(vector_store_ids=[vector_store.id]).resources,
    )
    print(f"Created agent: {agent.id}")

    # Ask a question that requires knowledge from the document
    thread = client.agents.threads.create()
    client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="What does our standards reference say about materiality determination?",
    )

    run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

    if run.status == "completed":
        messages = client.agents.messages.list(thread_id=thread.id)
        for msg in messages:
            if msg.role == "assistant":
                print(f"\nAgent response:\n{msg.content[0].text.value}")
                break

    # Clean up
    client.agents.delete_agent(agent.id)
    client.agents.delete_vector_store(vector_store.id)
    client.agents.delete_file(file.id)
    print("\nResources cleaned up.")


if __name__ == "__main__":
    main()
