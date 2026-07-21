from abc import ABC, abstractmethod

from careguard.models.schemas import NormalizedRequest, NormalizedResponse


class TargetConnector(ABC):
    @abstractmethod
    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        """Send a normalized request without exposing connector secrets."""

