# FIX: mirror_full_archive import path and failure detection

## Problem

`tools/mirror_full_archive.ps1` could print a success message even when the Python command failed with:

```text
ModuleNotFoundError: No module named 'backend'
```

The container command executed `/app/tools/mirror_full_archive.py` as a script, causing Python to put `/app/tools` on `sys.path` instead of the project root `/app`.

## Fix

- `tools/mirror_full_archive.py` now explicitly inserts the project root into `sys.path` before importing `backend.*`.
- `tools/mirror_full_archive.ps1` now runs Docker with `-w /app` and `PYTHONPATH=/app`.
- The PowerShell script now checks `$LASTEXITCODE` and fails loudly instead of printing a false completion message.
- The shell script was updated with the same working directory and `PYTHONPATH` behavior.

## Command

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\mirror_full_archive.ps1
```
