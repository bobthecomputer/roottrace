# Changelog

## 2024-05-07

- Initialisation du projet RootTrace v0.1.0.
- Mise en place de l'API FastAPI (`/health`, `/ingest`, `/graph`, `/export/proof`).
- Pipeline d'ingestion complet (détection type artefact, extraction, entités, audit, preuves ZIP).
- Génération de suggestions OSINT et graphe JSON minimal.
- Configuration via `.env`, migrations Alembic et scripts qualité (ruff, mypy, pytest, semgrep, pip-audit).

## 2024-05-08

- Ajout d'overrides mypy pour PIL, pytesseract, exifread, filetype et imagehash afin de stabiliser l'analyse stricte.
- Correction des colonnes JSON mutables (instanciation explicite) pour satisfaire SQLAlchemy et mypy.
- Typage des tests vidéo et harmonisation des imports pour maintenir la couverture et les linters.
