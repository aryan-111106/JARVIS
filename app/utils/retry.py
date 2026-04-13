import asyncio
import functools
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def async_retry(
    retries: int = 3,
    delay: float = 0.5,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: Exception | None = None
            for attempt in range(retries):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    if attempt < retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            raise last  # type: ignore[misc]

        return wrapper

    return decorator
