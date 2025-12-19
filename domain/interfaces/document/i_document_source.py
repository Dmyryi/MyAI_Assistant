from abc import ABC, abstractmethod
from typing import Iterator
from ...scenario_block import ScenarioBlock

class IDocumentSource(ABC):
    """Document source interface"""
    @abstractmethod
    def connect(self, resource_id: str) -> None:
        """Connects to document source"""
        pass
    
    @abstractmethod
    def extract_blocks(self) -> Iterator[ScenarioBlock]:
        """Extracts text blocks from document"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Checks if source is connected"""
        pass
