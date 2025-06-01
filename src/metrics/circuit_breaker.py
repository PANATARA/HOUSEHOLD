import enum
import functools
import time
from typing import Awaitable, Callable, ParamSpec, TypeVar

import httpx


class CircuitBreakerStateEnum(enum.Enum):
    closed = "CLOSED"
    half_open = "HALF_OPEN"
    open = "OPEN"


P = ParamSpec("P")
R = TypeVar("R")


class CircuitBreaker:
    def __init__(self, max_failures: int, reset_timeout: int):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerStateEnum.closed

    def __call__(
        self, func: Callable[P, Awaitable[R]]
    ) -> Callable[P, Awaitable[R | None]]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if not self.can_request:
                return None
            try:
                result = await func(*args, **kwargs)
            except httpx.RequestError:
                self.failure()
                return None
            else:
                self.success()
                return result

        return async_wrapper

    def success(self):
        self.failures = 0
        self.state = CircuitBreakerStateEnum.closed

    def failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.max_failures:
            self.state = CircuitBreakerStateEnum.open

    @property
    def can_request(self) -> bool:
        if self.state == CircuitBreakerStateEnum.open:
            if (time.time() - self.last_failure_time) > self.reset_timeout:
                self.state = CircuitBreakerStateEnum.half_open
                return True
            return False
        return True

    def reset(self) -> None:
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerStateEnum.closed
