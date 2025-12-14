# Repository Guidelines

## Project Structure & Module Organization
- `blog/`: Django project settings, URLs, WSGI/ASGI entrypoints.
- `myblog/`: Core app with models, serializers, signals, and API URL placeholder; tests live in `myblog/tests.py`.
- `manage.py`: Django management entry; run admin tasks from repo root.
- `study_docs/`: Internal docs (e.g., `fix_report.md` for past fixes).
- `db.sqlite3`: Default development database; avoid committing changes.

## Build, Test, and Development Commands
- Setup (Python 3.11): `python -m venv .venv && source .venv/bin/activate && pip install -e .`
- Migrations: `python manage.py makemigrations` then `python manage.py migrate`
- Run server: `python manage.py runserver`
- System check: `python manage.py check`
- Tests: `python manage.py test myblog`

## Coding Style & Naming Conventions
- Follow Django/DRF idioms; prefer explicit `verbose_name` and `related_name` on relations.
- Use snake_case for fields and methods; class names in PascalCase.
- Keep timestamps auto-managed (`auto_now_add/auto_now`); avoid manual datetime writes.
- Keep API serializers thin; add `custom_signup`-style hooks for extra fields.
- Default formatting: 4-space indentation; UTF-8 text; keep files ASCII unless needed.

## Testing Guidelines
- Primary framework: Django’s `TestCase`.
- Place tests in `myblog/tests.py` (or a `tests/` package); name test methods `test_<behavior>`.
- Include at least one test per model/serializer change; cover validation and permissions when applicable.
- Run `python manage.py test myblog` before sending a PR.

## Commit & Pull Request Guidelines
- Commit messages: short imperative summary (e.g., `Add tag count helper`, `Fix signup serializer`); group related changes.
- Pull requests should include: purpose, key changes, verification steps (`python manage.py check`, `python manage.py test myblog`), and migration notice if applicable.
- Attach screenshots or sample payloads for API/behavior changes when relevant.

## Security & Configuration Tips
- Do not commit secrets; use environment variables for prod settings (DB, email, storage).
- For media handling, ensure `MEDIA_ROOT`/`MEDIA_URL` are set; configure proper storage for non-dev environments.
- Keep `DEBUG=False` outside local development and set `ALLOWED_HOSTS` appropriately. 
