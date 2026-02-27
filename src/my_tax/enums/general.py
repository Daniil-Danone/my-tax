"""
Enums для общих сущностей
"""

from enum import Enum


class ClientType(str, Enum):
    """Тип клиента"""

    FROM_INDIVIDUAL = "FROM_INDIVIDUAL"
    FROM_LEGAL_ENTITY = "FROM_LEGAL_ENTITY"
    FROM_FOREIGN_AGENCY = "FROM_FOREIGN_AGENCY"