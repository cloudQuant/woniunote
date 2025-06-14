"""
WoniuNote Controller Package

This package contains Flask route controllers for the WoniuNote application.
"""

# Import key controllers to make them available at package level
try:
    from . import admin
    from . import article
    from . import card_center
    from . import comment
    from . import favorite
    from . import index
    from . import todo_center
    from . import ucenter
    from . import ueditor
    from . import user
except ImportError as e:
    # Handle import errors gracefully during development
    import warnings
    warnings.warn(f"Some controllers could not be imported: {e}")

__all__ = [
    'admin',
    'article',
    'card_center',
    'comment',
    'favorite',
    'index',
    'todo_center',
    'ucenter',
    'ueditor',
    'user'
]
