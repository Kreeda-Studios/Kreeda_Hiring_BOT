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

import time
import asyncio
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Singleton client instances for reuse across threads/event loops
_client_instance = None
_async_client_instance = None
_rate_limiter = None


# ============================================================================
# DISTRIBUTED RATE LIMITER (Redis Token Bucket / Fixed Window)
# ============================================================================

class OpenAIRateLimiter:
    """
    Distributed rate limiter using Redis to enforce RPM (Requests Per Minute)
    and TPM (Tokens Per Minute) limit pools across multiple Python worker containers.
    
    Uses an atomic Lua script to prevent race conditions during parallel requests.
    """
    
    def __init__(self):
        self.redis_client = None
        # Retrieve scale thresholds from environment variables (defaults to Tier 1 limits)
        self.max_rpm = int(os.getenv('OPENAI_MAX_RPM', '500'))
        self.max_tpm = int(os.getenv('OPENAI_MAX_TPM', '200000'))
        
        # Redis connection config from BullMQ environment setup
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_password = os.getenv('REDIS_PASSWORD', 'password123')
        
        # Lua script executes atomically within Redis to evaluate RPM and TPM counters.
        # Key 1: RPM counter for current minute.
        # Key 2: TPM counter for current minute.
        self.lua_script = """
        local rpm_key = KEYS[1]
        local tpm_key = KEYS[2]
        local current_time = tonumber(ARGV[1])
        local tokens_needed = tonumber(ARGV[2])
        local max_rpm = tonumber(ARGV[3])
        local max_tpm = tonumber(ARGV[4])

        local current_rpm = tonumber(redis.call('GET', rpm_key) or '0')
        local current_tpm = tonumber(redis.call('GET', tpm_key) or '0')

        if current_rpm + 1 > max_rpm or current_tpm + tokens_needed > max_tpm then
            local seconds_left = 60 - (current_time % 60)
            return {0, seconds_left}
        else
            redis.call('INCRBY', rpm_key, 1)
            redis.call('INCRBY', tpm_key, tokens_needed)
            redis.call('EXPIRE', rpm_key, 60)
            redis.call('EXPIRE', tpm_key, 60)
            return {1, 0}
        end
        """
        self._lua_sha = None

    async def _get_redis(self):
        """Lazy initialization of async Redis client connection pool"""
        if self.redis_client is None:
            try:
                self.redis_client = aioredis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Failing open...")
                self.redis_client = False
        return self.redis_client

    async def acquire(self, tokens_needed: int) -> int:
        """
        Acquires rate limiting tokens. If limits are hit, pauses/sleeps and retries.
        Fails open if Redis is down or unreachable to protect service availability.
        """
        redis = await self._get_redis()
        if not redis:
            return tokens_needed

        current_time = int(time.time())
        minute_bucket = current_time // 60
        rpm_key = f"openai:limiter:RPM:{minute_bucket}"
        tpm_key = f"openai:limiter:TPM:{minute_bucket}"

        attempt = 0
        while attempt < 30: # Hard limit on loop iterations to prevent hanging workers indefinitely
            try:
                if self._lua_sha is None:
                    self._lua_sha = await redis.script_load(self.lua_script)
                
                result = await redis.evalsha(
                    self._lua_sha,
                    2,
                    rpm_key,
                    tpm_key,
                    current_time,
                    tokens_needed,
                    self.max_rpm,
                    self.max_tpm
                )
                
                allowed, wait_seconds = result[0], result[1]
                if allowed == 1:
                    return tokens_needed
                
                wait_seconds = max(1, wait_seconds)
                logger.info(f"⏳ OpenAI Rate Limiter: Limit reached. Waiting {wait_seconds}s...")
                await asyncio.sleep(wait_seconds)
                
                # Recalculate time coordinates for retry window
                current_time = int(time.time())
                minute_bucket = current_time // 60
                rpm_key = f"openai:limiter:RPM:{minute_bucket}"
                tpm_key = f"openai:limiter:TPM:{minute_bucket}"
                attempt += 1
            except Exception as e:
                logger.warning(f"⚠️ Redis Rate Limiter error: {e}. Failing open...")
                return tokens_needed
                
        return tokens_needed

    async def refund(self, tokens_to_refund: int):
        """Refund unused tokens back to the current Redis minute bucket"""
        if tokens_to_refund <= 0:
            return
        redis = await self._get_redis()
        if not redis:
            return
            
        current_time = int(time.time())
        minute_bucket = current_time // 60
        tpm_key = f"openai:limiter:TPM:{minute_bucket}"
        
        try:
            exists = await redis.exists(tpm_key)
            if exists:
                current_tpm = int(await redis.get(tpm_key) or '0')
                to_decr = min(tokens_to_refund, current_tpm)
                if to_decr > 0:
                    await redis.decrby(tpm_key, to_decr)
        except Exception as e:
            logger.warning(f"⚠️ Redis Rate Limiter refund error: {e}")


# ============================================================================
# RATE LIMITED CLIENT PROXY WRAPPERS
# ============================================================================

class RateLimitedAsyncOpenAI:
    """
    Proxy wrapper for AsyncOpenAI client.
    Intercepts target namespaces (chat, embeddings, responses) to route
    calls through the Redis rate limiter automatically.
    """
    def __init__(self, client, limiter):
        self._client = client
        self._limiter = limiter
        self.chat = RateLimitedChat(client.chat, limiter)
        self.embeddings = RateLimitedEmbeddings(client.embeddings, limiter)
        if hasattr(client, "responses"):
            self.responses = RateLimitedResponses(client.responses, limiter)
            
    def __getattr__(self, name):
        # Fallback to standard client attributes and methods
        return getattr(self._client, name)


class RateLimitedChat:
    def __init__(self, chat, limiter):
        self.completions = RateLimitedCompletions(chat.completions, limiter)


class RateLimitedCompletions:
    def __init__(self, completions, limiter):
        self._completions = completions
        self._limiter = limiter

    async def create(self, *args, **kwargs):
        # Estimate input prompt tokens using whitespace heuristics
        messages = kwargs.get("messages", [])
        prompt_text = ""
        for m in messages:
            if isinstance(m, dict):
                prompt_text += m.get("content", "")
                
        input_tokens = int(len(prompt_text.split()) * 1.3)
        max_tokens = kwargs.get("max_tokens", 4000) or 4000
        estimated_tokens = input_tokens + max_tokens
        
        logger.info(f"🔑 [RATE LIMIT] Acquiring tokens for Completion (Est: {estimated_tokens} | Input: {input_tokens})")
        acquired_tpm = await self._limiter.acquire(estimated_tokens)
        
        try:
            response = await self._completions.create(*args, **kwargs)
            # Refund unused buffer back to the token pool
            if hasattr(response, "usage") and response.usage and response.usage.total_tokens:
                actual = response.usage.total_tokens
                logger.info(f"💸 [RATE LIMIT] Completion Used: {actual} tokens | Refunded: {acquired_tpm - actual} unused tokens.")
                if actual < acquired_tpm:
                    await self._limiter.refund(acquired_tpm - actual)
            else:
                logger.info(f"💸 [RATE LIMIT] Completion succeeded (Usage metadata missing).")
            return response
        except Exception as e:
            # Reclaim locked capacity on error
            await self._limiter.refund(acquired_tpm)
            err_type = type(e).__name__
            if err_type in ('BadRequestError', 'AuthenticationError', 'PermissionDeniedError'):
                raise Exception(f"[DETERMINISTIC] OpenAI {err_type}: {str(e)}") from e
            else:
                raise Exception(f"[TRANSIENT] OpenAI {err_type}: {str(e)}") from e


class RateLimitedEmbeddings:
    def __init__(self, embeddings, limiter):
        self._embeddings = embeddings
        self._limiter = limiter

    async def create(self, *args, **kwargs):
        input_val = kwargs.get("input", "")
        if isinstance(input_val, list):
            input_text = " ".join([str(t) for t in input_val])
        else:
            input_text = str(input_val)
            
        estimated_tokens = int(len(input_text.split()) * 1.3)
        estimated_tokens = max(1, estimated_tokens)
        
        logger.info(f"🔑 [RATE LIMIT] Acquiring {estimated_tokens} tokens for Embeddings request.")
        await self._limiter.acquire(estimated_tokens)
        
        try:
            response = await self._embeddings.create(*args, **kwargs)
            logger.info(f"💸 [RATE LIMIT] Embeddings completed.")
            return response
        except Exception as e:
            await self._limiter.refund(estimated_tokens)
            err_type = type(e).__name__
            if err_type in ('BadRequestError', 'AuthenticationError', 'PermissionDeniedError'):
                raise Exception(f"[DETERMINISTIC] OpenAI {err_type}: {str(e)}") from e
            else:
                raise Exception(f"[TRANSIENT] OpenAI {err_type}: {str(e)}") from e


class RateLimitedResponses:
    def __init__(self, responses, limiter):
        self._responses = responses
        self._limiter = limiter

    async def parse(self, *args, **kwargs):
        messages = kwargs.get("input", [])
        prompt_text = ""
        for m in messages:
            if isinstance(m, dict):
                prompt_text += m.get("content", "")
                
        input_tokens = int(len(prompt_text.split()) * 1.3)
        max_tokens = kwargs.get("max_tokens", 4000) or 4000
        estimated_tokens = input_tokens + max_tokens
        
        logger.info(f"🔑 [RATE LIMIT] Acquiring tokens for Structured Parse (Est: {estimated_tokens} | Input: {input_tokens})")
        acquired_tpm = await self._limiter.acquire(estimated_tokens)
        
        try:
            response = await self._responses.parse(*args, **kwargs)
            if hasattr(response, "usage") and response.usage and response.usage.total_tokens:
                actual = response.usage.total_tokens
                logger.info(f"💸 [RATE LIMIT] Structured Parse Used: {actual} tokens | Refunded: {acquired_tpm - actual} unused tokens.")
                if actual < acquired_tpm:
                    await self._limiter.refund(acquired_tpm - actual)
            else:
                logger.info(f"💸 [RATE LIMIT] Structured Parse succeeded (Usage metadata missing).")
            return response
        except Exception as e:
            await self._limiter.refund(acquired_tpm)
            err_type = type(e).__name__
            if err_type in ('BadRequestError', 'AuthenticationError', 'PermissionDeniedError'):
                raise Exception(f"[DETERMINISTIC] OpenAI {err_type}: {str(e)}") from e
            else:
                raise Exception(f"[TRANSIENT] OpenAI {err_type}: {str(e)}") from e


# ============================================================================
# CLIENT INITIALIZERS
# ============================================================================

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
    """Get or create async OpenAI client instance (Rate Limited)"""
    global _async_client_instance, _rate_limiter
    
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    if _async_client_instance is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        raw_client = AsyncOpenAI(api_key=api_key)
        
        if _rate_limiter is None:
            _rate_limiter = OpenAIRateLimiter()
            
        _async_client_instance = RateLimitedAsyncOpenAI(raw_client, _rate_limiter)
    
    return _async_client_instance


def create_chat_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
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
    model: str = "gpt-4o-mini",
    temperature: float = 0.0
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
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response)


async def parse_json_response_async(
    prompt: str,
    system_prompt: str = "You are a helpful assistant that responds only in valid JSON format.",
    model: str = "gpt-4o-mini",
    temperature: float = 0.0
) -> Dict[str, Any]:
    """
    Get a JSON response from OpenAI (async version)
    
    Args:
        prompt: User prompt
        system_prompt: System prompt
        model: Model to use
        
    Returns:
        Parsed JSON dictionary
    """
    import json
    
    client = get_async_openai_client()
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
