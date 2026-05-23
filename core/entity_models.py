"""
Entity Models Module

Defines all entity types and their relationships for the knowledge graph.
Follows the first-principles approach: code is a structured system of entities and relations.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    FILE = "file"
    CLASS = "class"
    METHOD = "method"
    PROPERTY = "property"
    COMPONENT = "component"
    INTERFACE = "interface"
    ENUM = "enum"


class RelationType(Enum):
    """Types of relationships between entities."""
    CONTAINS = "contains"           # File contains Class
    DECLARES = "declares"           # Class declares Method
    CALLS = "calls"                 # Method calls Method
    INHERITS = "inherits"           # Class inherits Class
    IMPLEMENTS = "implements"       # Class implements Interface
    USES = "uses"                   # Method uses Property
    NESTS = "nests"                 # Component nests Component
    IMPORTS = "imports"             # File imports File


@dataclass
class SourceLocation:
    """Represents a location in source code."""
    file_path: str
    line_number: int
    column_number: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number
        }


@dataclass
class Entity:
    """Base class for all knowledge graph entities."""
    id: str
    name: str
    entity_type: EntityType
    location: SourceLocation
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "location": self.location.to_dict(),
            "metadata": self.metadata
        }


@dataclass
class FileEntity(Entity):
    """Represents a source code file."""
    relative_path: str = ""
    absolute_path: str = ""
    imports: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.entity_type = EntityType.FILE
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "imports": self.imports
        })
        return base


@dataclass
class ClassEntity(Entity):
    """Represents a class or component in ArkTS."""
    file_id: str = ""
    is_component: bool = False
    is_entry: bool = False
    is_exported: bool = False
    decorators: List[str] = field(default_factory=list)
    parent_class: Optional[str] = None
    implemented_interfaces: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.is_component:
            self.entity_type = EntityType.COMPONENT
        else:
            self.entity_type = EntityType.CLASS
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "file_id": self.file_id,
            "is_component": self.is_component,
            "is_entry": self.is_entry,
            "is_exported": self.is_exported,
            "decorators": self.decorators,
            "parent_class": self.parent_class,
            "implemented_interfaces": self.implemented_interfaces
        })
        return base


@dataclass
class MethodEntity(Entity):
    """Represents a method or function."""
    class_id: str = ""
    is_static: bool = False
    is_async: bool = False
    is_private: bool = False
    is_protected: bool = False
    is_public: bool = True
    return_type: str = "void"
    parameters: List[Dict[str, str]] = field(default_factory=list)
    
    def __post_init__(self):
        self.entity_type = EntityType.METHOD
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "class_id": self.class_id,
            "is_static": self.is_static,
            "is_async": self.is_async,
            "is_private": self.is_private,
            "is_protected": self.is_protected,
            "is_public": self.is_public,
            "return_type": self.return_type,
            "parameters": self.parameters
        })
        return base


@dataclass
class PropertyEntity(Entity):
    """Represents a property or field."""
    class_id: str = ""
    property_type: str = ""
    is_static: bool = False
    is_readonly: bool = False
    is_optional: bool = False
    default_value: Optional[str] = None
    
    def __post_init__(self):
        self.entity_type = EntityType.PROPERTY
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "class_id": self.class_id,
            "property_type": self.property_type,
            "is_static": self.is_static,
            "is_readonly": self.is_readonly,
            "is_optional": self.is_optional,
            "default_value": self.default_value
        })
        return base


@dataclass
class Relation:
    """Represents a relationship between two entities."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "metadata": self.metadata
        }


@dataclass
class KnowledgeGraph:
    """Container for all entities and relations."""
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: Dict[str, Relation] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self.entities[entity.id] = entity
    
    def add_relation(self, relation: Relation) -> None:
        """Add a relation to the graph."""
        self.relations[relation.id] = relation
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_relations_by_source(self, source_id: str) -> List[Relation]:
        """Get all relations originating from a source entity."""
        return [r for r in self.relations.values() if r.source_id == source_id]
    
    def get_relations_by_target(self, target_id: str) -> List[Relation]:
        """Get all relations pointing to a target entity."""
        return [r for r in self.relations.values() if r.target_id == target_id]
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities.values() if e.entity_type == entity_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire graph to a dictionary."""
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relations": {k: v.to_dict() for k, v in self.relations.items()},
            "statistics": {
                "total_entities": len(self.entities),
                "total_relations": len(self.relations),
                "entity_types": {
                    et.value: len(self.get_entities_by_type(et))
                    for et in EntityType
                }
            }
        }
