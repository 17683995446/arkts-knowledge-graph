"""
Database Module

Provides data persistence layer for the knowledge graph.
"""

from .schema_definitions import (
    CREATE_TABLES_SQL,
    CLEAR_ALL_DATA_SQL,
    GET_STATISTICS_SQL,
    FIND_ORPHANS_SQL
)
from .knowledge_repository import KnowledgeRepository

__all__ = [
    'CREATE_TABLES_SQL',
    'CLEAR_ALL_DATA_SQL',
    'GET_STATISTICS_SQL',
    'FIND_ORPHANS_SQL',
    'KnowledgeRepository'
]
