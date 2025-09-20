# Decision Log

- SQLite moteur synchrone conservé pour v0.1 (asynchrone reporté, complexité inutile pour MVP).
- Extraction vidéo : fallback silencieux quand ffmpeg absent pour respecter le mode offline-first.
- OCR dépend de Tesseract natif ; fallback propre si non installé pour maintenir les tests.
- Mypy overrides ajoutés pour PIL/imagehash/pytesseract faute de stubs stables; évite crashs strict tout en gardant dépendances upstream.
