from typing import Any


MAX_MESSAGES_PER_THREAD = 10
THREAD_MEMORY: dict[str, list[dict[str, str]]] = {}


# This function returns the saved conversation messages for one thread.
def get_thread_messages(thread_id: str) -> list[dict[str, str]]:
    messages = THREAD_MEMORY.get(thread_id, [])
    return list(messages)


# This function saves one new message inside a thread's short-term memory.
def add_thread_message(thread_id: str, role: str, content: str) -> None:
    if thread_id not in THREAD_MEMORY:
        THREAD_MEMORY[thread_id] = []

    THREAD_MEMORY[thread_id].append({"role": role, "content": content})
    THREAD_MEMORY[thread_id] = THREAD_MEMORY[thread_id][-MAX_MESSAGES_PER_THREAD:]


# This function returns the whole in-memory store for quick debugging.
def get_memory_snapshot() -> dict[str, list[dict[str, str]]]:
    snapshot: dict[str, list[dict[str, str]]] = {}

    for thread_id, messages in THREAD_MEMORY.items():
        snapshot[thread_id] = list(messages)

    return snapshot


# This function clears memory for one thread or for all threads.
def clear_thread_memory(thread_id: str | None = None) -> None:
    if thread_id is None:
        THREAD_MEMORY.clear()
        return

    THREAD_MEMORY.pop(thread_id, None)
