"""
Web Module

Provides the Flask web server for the knowledge graph visualization.
"""

from .server_application import KnowledgeGraphServer, server, create_application

__all__ = [
    'KnowledgeGraphServer',
    'server',
    'create_application'
]
