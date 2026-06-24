# CI/CD Önerisi

Minimum GitHub Actions akışı:

```yaml
name: validate
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: pip install -r requirements-api.txt -r requirements-dev.txt
      - run: python -m compileall -q .
      - run: python tools/validate_project.py
      - run: python -m pytest -q
      - run: cd frontend && npm ci && npm run build
      - run: docker compose -f docker-compose.web.yml config
        env:
          MEDEK_API_SECRET: CHANGE_ME_CI_ONLY_64_CHAR_SECRET_1234567890_ABCDEFG
```

İleri aşamada eklenebilir:

- coverage report
- Trivy image scan
- release zip üretimi
- staging deployment
