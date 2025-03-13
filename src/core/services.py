from abc import ABCMeta, abstractmethod
import asyncio
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar('T')

class BaseService(Generic[T], metaclass=ABCMeta):
    """
    An abstract base class for services that require validation before processing.
    It provides methods for running validators and processing the main logic.

    Methods:
        get_validators() -> list[Callable]:
            Returns a list of validator functions. By default, returns an empty list.

        validate() -> None:
            Executes all validators returned by `get_validators`. Assumes validators are async.

        run_process() -> any:
            Runs validation and then executes the `process` method. Handles both sync and async validation.

        process() -> any:
            Abstract method that must be implemented in subclasses to define the main processing logic.
    """

    def get_validators(self) -> list[Callable]:
        return []

    async def validate(self) -> None:
        validators = self.get_validators()
        for validator in validators:
            if asyncio.iscoroutinefunction(validator):
                await validator()
            else:
                validator()

    async def run_process(self) -> T:
        if asyncio.iscoroutinefunction(self.validate):
            await self.validate()
        else:
            self.validate()
        return await self.process()

    @abstractmethod
    async def process(self) -> T:
        raise NotImplementedError("Please implement in the service class")
