#!/usr/bin/env python3
"""
OpenAI Client for Kreeda Hiring Bot
Provides a centralized OpenAI client for AI processing tasks.
"""

import os
from typing import List, Dict, Any, Optional

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    AsyncOpenAI = None

# Singleton client instances
_client_instance = None
_async_client_instance = None

def get_openai_client():
    """Get or create OpenAI client instance"""
    global _client_instance
    
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    if _client_instance is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client_instance = OpenAI(api_key=api_key)
    
    return _client_instance

# Alias for backward compatibility
openai_client = get_openai_client


def get_async_openai_client():
    """Get or create async OpenAI client instance"""
    global _async_client_instance
    
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    if _async_client_instance is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _async_client_instance = AsyncOpenAI(api_key=api_key)
    
    return _async_client_instance


def create_chat_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    response_format: Optional[Dict] = None
) -> str:
    """
    Create a chat completion using OpenAI API
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: OpenAI model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        response_format: Optional response format (e.g., {"type": "json_object"})
        
    Returns:
        Generated text response
    """
    client = get_openai_client()
    
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def create_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Create text embedding using OpenAI API
    
    Args:
        text: Text to embed
        model: Embedding model to use
        
    Returns:
        List of embedding floats
    """
    client = get_openai_client()
    
    response = client.embeddings.create(
        model=model,
        input=text
    )
    
    return response.data[0].embedding


async def create_embedding_async(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Create text embedding using OpenAI API (async version)
    
    Args:
        text: Text to embed
        model: Embedding model to use
        
    Returns:
        List of embedding floats
    """
    client = get_async_openai_client()
    
    response = await client.embeddings.create(
        model=model,
        input=text
    )
    
    return response.data[0].embedding


def create_embeddings_batch(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Create embeddings for multiple texts in batch
    
    Args:
        texts: List of texts to embed
        model: Embedding model to use
        
    Returns:
        List of embedding vectors
    """
    client = get_openai_client()
    
    response = client.embeddings.create(
        model=model,
        input=texts
    )
    
    return [item.embedding for item in response.data]


async def create_embeddings_batch_async(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Create embeddings for multiple texts in batch (async version)
    
    Args:
        texts: List of texts to embed
        model: Embedding model to use
        
    Returns:
        List of embedding vectors
    """
    client = get_async_openai_client()
    
    response = await client.embeddings.create(
        model=model,
        input=texts
    )
    
    return [item.embedding for item in response.data]


def parse_json_response(
    prompt: str,
    system_prompt: str = "You are a helpful assistant that responds only in valid JSON format.",
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Get a JSON response from OpenAI
    
    Args:
        prompt: User prompt
        system_prompt: System prompt
        model: Model to use
        
    Returns:
        Parsed JSON dictionary
    """
    import json
    
    response = create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        model=model,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response)
