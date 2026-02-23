"""
03 — Adding Knowledge (File Search and Vector Stores)

Uploads a document (audit standards reference) to Azure AI Foundry, creates
a vector store for retrieval, and attaches it to an agent via the
FileSearchTool so the agent can ground its answers in the document.

Concepts: file upload, vector stores, FileSearchTool, grounded responses
"""

import os
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AgentStreamEvent, FileSearchTool, FilePurpose
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = Path(__file__).parent / "outputs"


def main():
    client = AgentsClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=AzureCliCredential(),
    )

    # Upload a knowledge document
    data_path = os.path.join(SCRIPT_DIR, "data", "sample_audit_standards.md")
    file = client.files.upload_and_poll(
        file_path=data_path,
        purpose=FilePurpose.AGENTS,
    )
    print(f"Uploaded file: {file.id}")

    # Create a vector store from the uploaded file
    vector_store = client.vector_stores.create_and_poll(
        file_ids=[file.id],
        name="audit-standards-kb",
    )
    print(f"Created vector store: {vector_store.id}")

    # Create an agent with file search grounding
    agent = client.create_agent(
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
    thread = client.threads.create()
    client.messages.create(
        thread_id=thread.id,
        role="user",
        content="What does our standards reference say about materiality determination?",
    )

    # Stream the response and log tool usage
    response_chunks: list[str] = []
    file_search_invoked = False

    print("\nStreaming response:")
    with client.runs.stream(thread_id=thread.id, agent_id=agent.id) as stream:
        for event_type, event_data, _ in stream:
            if event_type == AgentStreamEvent.THREAD_RUN_STEP_CREATED:
                if event_data.type == "tool_calls":
                    print(f"  [tool step created] type={event_data.type}")
            elif event_type == AgentStreamEvent.THREAD_RUN_STEP_COMPLETED:
                if event_data.type == "tool_calls":
                    for tool_call in event_data.step_details.tool_calls:
                        tool_type = tool_call.get("type", "unknown")
                        print(f"  ✓ Tool call completed: {tool_type}")
                        if tool_type == "file_search":
                            file_search_invoked = True
            elif event_type == AgentStreamEvent.THREAD_MESSAGE_DELTA:
                for part in event_data.delta.content:
                    if hasattr(part, "text") and part.text:
                        text = part.text.value
                        print(text, end="", flush=True)
                        response_chunks.append(text)
    print()

    if file_search_invoked:
        print("\n✓ FileSearchTool was invoked — response is grounded in the uploaded document.")
    else:
        print("\n✗ FileSearchTool was NOT invoked — the agent did not search the knowledge base.")

    # Write the response to a markdown file
    response_text = "".join(response_chunks)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = OUTPUTS_DIR / "03_knowledge.md"
    output_file.write_text(response_text, encoding="utf-8")
    print(f"Response saved to {output_file}")

    # Clean up
    client.delete_agent(agent.id)
    client.vector_stores.delete(vector_store.id)
    client.files.delete(file.id)
    print("Resources cleaned up.")


if __name__ == "__main__":
    main()
