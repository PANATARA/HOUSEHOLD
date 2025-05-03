import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


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
        """Returns a list of validator functions."""
        return []

    async def validate(self) -> None:
        """Executes all validators (both sync and async)."""
        validators = self.get_validators()
        tasks = []

        for validator in validators:
            if asyncio.iscoroutinefunction(validator):
                tasks.append(validator())  # Собираем асинхронные задачи
            else:
                validator()  # Вызываем синхронные валидаторы сразу

        if tasks:
            await asyncio.gather(
                *tasks
            )  # Дожидаемся выполнения всех асинхронных валидаторов

    async def run_process(self) -> T:
        """Runs validation and then executes the `process` method."""
        await self.validate()
        return await self.process()

    @abstractmethod
    async def process(self) -> T:
        """Abstract method that must be implemented in subclasses."""
        raise NotImplementedError("Please implement in the service class")
