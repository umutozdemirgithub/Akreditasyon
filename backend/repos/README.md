# Repository split plan

`backend.repositories` is still kept as a compatibility module for the current
release. The modules in this directory group the public repository functions by
bounded context so future router code can import from focused modules first.

Next safe refactor step:

1. Move implementations from `backend.repositories` into these modules one group at a time.
2. Keep `backend.repositories` as a temporary re-export layer.
3. After tests pass, update routers to import only from `backend.repos.*`.
4. Remove the monolith once all imports are migrated.
