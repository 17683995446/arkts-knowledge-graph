"""
Core Module

Contains fundamental components for the ArkTS Knowledge Graph system.
"""

from .config_manager import ConfigurationManager, config
from .entity_models import (
    EntityType,
    RelationType,
    SourceLocation,
    Entity,
    FileEntity,
    ClassEntity,
    MethodEntity,
    PropertyEntity,
    Relation,
    KnowledgeGraph
)

__all__ = [
    'ConfigurationManager',
    'config',
    'EntityType',
    'RelationType',
    'SourceLocation',
    'Entity',
    'FileEntity',
    'ClassEntity',
    'MethodEntity',
    'PropertyEntity',
    'Relation',
    'KnowledgeGraph'
]
