import re
from typing import Any, Dict, List

PROMPT_LIMIT = 3750  # Note: This measures CHARACTERS. ~900 tokens.


def chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """Splits text into chunks of roughly `chunk_size` characters, preserving complete sentences."""
    if not text:
        return []

    # Clean line breaks and split by sentence boundaries while preserving punctuation
    text_normalized = text.replace('\r\n', '\n')
    # Regex split that captures sentence endings (. ! ?) followed by space or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text_normalized)
    
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_clean = sentence.strip()
        if not sentence_clean:
            continue

        # Calculate length including space separator if chunk already has items
        sentence_len = len(sentence_clean) + (1 if current_chunk else 0)

        # Append sentence to chunk, or start a new chunk if limit is exceeded
        if current_length + sentence_len <= chunk_size or not current_chunk:
            current_chunk.append(sentence_clean)
            current_length += sentence_len
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence_clean]
            current_length = len(sentence_clean)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def build_prompt(query: str, context_chunks: List[str], prompt_limit: int = PROMPT_LIMIT) -> str:
    """Builds a RAG prompt fitting maximum context chunks within `prompt_limit` characters."""
    prompt_start = (
        "Answer the question based on the context below. "
        "If you don't know the answer based on the context provided below, "
        "just respond with 'I don't know' instead of making up an answer. "
        "Don't start your response with the word 'Answer:'.\n\nContext:\n"
    )
    prompt_end = f"\n\nQuestion: {query}\nAnswer:"

    # Account for static wrapper length to prevent character overflow
    available_limit = max(0, prompt_limit - len(prompt_start) - len(prompt_end))
    
    selected_chunks: List[str] = []
    current_length = 0

    for chunk in context_chunks:
        # "\n\n---\n\n" separator is 7 characters long
        separator_len = 7 if selected_chunks else 0
        
        if current_length + len(chunk) + separator_len > available_limit:
            break
            
        selected_chunks.append(chunk)
        current_length += len(chunk) + separator_len

    context_str = "\n\n---\n\n".join(selected_chunks)
    return f"{prompt_start}{context_str}{prompt_end}"


def construct_messages_list(chat_history: List[Dict[str, Any]], prompt: str) -> List[Dict[str, str]]:
    """Constructs OpenAI API messages format with proper role mappings and boundary checks."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": "You are a helpful assistant."}]
    
    for message in chat_history:
        role = "assistant" if message.get("isBot") else "user"
        messages.append({"role": role, "content": message.get("text", "")})

    # Safely attach or replace latest user prompt at the tail of the message stream
    if len(messages) > 1 and messages[-1]["role"] == "user":
        messages[-1]["content"] = prompt
    else:
        messages.append({"role": "user", "content": prompt})
        
    return messages
