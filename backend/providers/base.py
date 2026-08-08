"""Interfaz base para proveedores de datos financieros."""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDataProvider(ABC):

    @abstractmethod
    def fetch_raw_data(self, symbol: str) -> Dict[str, Any]:
        """Retorna un diccionario estructurado con los datos crudos del símbolo."""
        pass
