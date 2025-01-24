from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Any

class BaseService(metaclass=ABCMeta):

    async def __call__(self) -> Any:
        await self.validate()
        return await self.execute()

    def get_validators(self) -> list[Callable]:
        return []

    async def validate(self) -> None:
        validators = self.get_validators()
        for validator in validators:
            await validator()

    @abstractmethod
    async def execute(self) -> Any:
        raise NotImplementedError("Please implement in the service class")
