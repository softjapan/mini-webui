from typing import Any, Dict, List, Optional, Iterator
import logging

from fastapi import HTTPException, status
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError, RateLimitError, BadRequestError

from ..config import OPENAI_API_KEY, OPENAI_API_BASE

log = logging.getLogger("mini_webui.openai")


def get_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
    key = api_key or OPENAI_API_KEY
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OPENAI_API_KEY is not configured")
    return OpenAI(api_key=key, base_url=base_url or OPENAI_API_BASE)


def chat_completion(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    """Call OpenAI Chat Completions API and return assistant content.

    Raises HTTPException on API errors to propagate meaningful status codes.
    """
    client = get_client(api_key=api_key, base_url=base_url)
    log.info(f"OpenAI chat_completion: model=%s, temp=%s, msgs=%d", model, temperature, len(messages))

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        choice = resp.choices[0]
        content = choice.message.content or ""
        log.info("OpenAI chat_completion: received %d chars", len(content or ""))
        return content
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except APIConnectionError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def stream_chat_completion(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Iterator[str]:
    """Yield assistant content chunks from OpenAI as they arrive.

    Yields plain text chunks (no SSE framing). Caller can wrap for SSE.
    """
    client = get_client(api_key=api_key, base_url=base_url)
    log.info(f"OpenAI stream_chat: model=%s, temp=%s, msgs=%d", model, temperature, len(messages))
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and getattr(delta, "content", None):
                    piece = delta.content  # type: ignore[attr-defined]
                    log.debug("OpenAI stream_chat: chunk len=%d", len(piece or ""))
                    yield piece
            except Exception:
                continue
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except APIConnectionError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
