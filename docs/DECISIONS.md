# Decision Log

- SQLite moteur synchrone conservé pour v0.1 (asynchrone reporté, complexité inutile pour MVP).
- Extraction vidéo : fallback silencieux quand ffmpeg absent pour respecter le mode offline-first.
- OCR dépend de Tesseract natif ; fallback propre si non installé pour maintenir les tests.
- Mypy overrides ajoutés pour PIL/imagehash/pytesseract faute de stubs stables; évite crashs strict tout en gardant dépendances upstream.
- Interfaces locales : FastAPI+Jinja2 pour le web et Tkinter (stdlib) pour le desktop afin de rester cross-OS sans dépendances propriétaires.
- Pont exécutable : PyInstaller déclenché via CLI en dry-run par défaut pour respecter la philosophie offline-first (aucune compilation forcée).
