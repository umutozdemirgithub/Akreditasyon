# Updated Test Report

Executed checks for the personal role-scoped backup release.

```bash
python -m compileall -q backend tools/mirror_full_archive.py
pytest -q tests/test_personal_role_scoped_backup.py tests/test_readable_archive_mirror.py tests/test_organizational_storage_hierarchy.py tests/test_section_autosave_draft_guard.py tests/test_export_download_empty_report_and_rate_limit.py tests/test_api_unhealthy_boot_guard.py tests/test_role_based_help_manual.py
# 28 passed

cd frontend
npm ci --no-audit --no-fund
npm run build
# build successful
```
