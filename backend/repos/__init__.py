"""Repository-layer compatibility package.

The legacy `backend.repositories` module remains the source of truth during the
incremental refactor. New code should import from the focused modules in this
package so functions can be moved out of the monolith gradually without changing
API behavior.
"""
