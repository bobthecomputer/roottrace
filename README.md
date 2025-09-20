# RootTrace

RootTrace est un service d'ingestion **local-first** pour les analystes OSINT et forensics. Il traite des artefacts (fichiers ou URL), extrait le texte et les métadonnées, détecte des entités clefs puis prépare un paquet de preuve exploitable hors ligne.

## Fonctionnalités

- API FastAPI (`/health`, `/ingest`, `/graph`, `/export/proof`).
- Détection automatique du type d'artefact (image, vidéo, PDF, texte) avec hachage SHA-256.
- Extraction :
  - OCR Tesseract + EXIF + pHash pour les images.
  - Texte et métadonnées PDF via `pdfminer.six`.
  - Keyframe & métadonnées vidéo via `ffmpeg` (avec fallback propre si absent).
  - Lecture texte brut UTF-8.
- Détection d'entités (emails, domaines, téléphones, montants, indices "paye").
- Génération de suggestions OSINT (subfinder/dnsx, theHarvester, crt.sh, ArchiveBox, EmailRep).
- Traçabilité : audit JSONL avec rédaction, journalisation en base et paquet de preuve compressé (artefacts, logs, métadonnées).
- Graphe JSON minimal (noeuds artefacts ↔ entités) prêt pour une future UI.
- Configuration locale via variables d'environnement (`ROOTTRACE_*`).

## Installation

1. Créer et activer un environnement Python 3.11.
2. Installer les dépendances :

```bash
pip install -r requirements-dev.txt
```

3. Installer les binaires optionnels :
   - [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html)
   - [FFmpeg](https://ffmpeg.org/download.html) (pour l'extraction keyframe)

4. Initialiser la base SQLite (facultatif, sinon auto-création au démarrage) :

```bash
alembic upgrade head
```

## Configuration

Un fichier `.env.example` est fourni. Copier le en `.env` puis ajuster :

- `ROOTTRACE_DATA_DIR` : dossier de stockage des artefacts.
- `ROOTTRACE_PROOF_DIR` : dossier d'export des preuves.
- `ROOTTRACE_LOG_DIR` : journaux d'audit JSONL.
- `ROOTTRACE_DB_PATH` : chemin vers la base SQLite.
- `ROOTTRACE_ENABLE_NETWORK_FETCH=false` : garde l'ingestion offline par défaut.
- `ROOTTRACE_LEGAL_NOTE` : justification obligatoire avant d'activer les scrapers fallback.

## Lancement du service

```bash
uvicorn roottrace.api.main:app --reload
```

### Exemple d'appel API

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -F "file=@/chemin/vers/document.pdf" \
  -F "source_uri=poste1"
```

Réponse :

```json
{
  "job": {
    "id": 1,
    "artifact_kind": "pdf",
    "summary": {"entities": 3, "entity_kinds": ["email", "domain"], "proof_archive": "proofs/job-1.zip"},
    "text_excerpt": "..."
  },
  "entities": [ ... ],
  "suggestions": [ ... ]
}
```

Téléchargement du paquet de preuve :

```bash
curl -X POST http://127.0.0.1:8000/export/proof \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1}' \
  --output job-1.zip
```

### Graphe minimal

`GET /graph` renvoie :

```json
{
  "nodes": [{"id": "job:1", "type": "ingest", "label": "document.pdf"}, ...],
  "edges": [{"source": "job:1", "target": "entity:email:analyste@example.com", "type": "mentions"}]
}
```

## Qualité & Tests

La CI locale impose :

```bash
ruff check .
mypy .
pytest
semgrep --config p/ci
pip-audit
```

Le seuil de couverture doit rester ≥ 85 %. Les paquets de preuve sont générés dans `ROOTTRACE_PROOF_DIR`.
Des overrides mypy sont fournis pour PIL/pytesseract/imagehash/exifread/filetype afin de conserver le mode strict malgré l'absence de stubs.

## Notes de conformité

- **Offline-first** : aucun appel réseau n'est effectué sans `ROOTTRACE_ENABLE_NETWORK_FETCH=true`.
- **Scrapers X/Instagram** : `ScraperManager` refuse l'activation sans base légale (`ROOTTRACE_LEGAL_NOTE`).
- **Redaction** : emails/téléphones masqués dans les journaux JSONL.
- **Rétention** : valeur par défaut 30 jours via `ROOTTRACE_RETENTION_DAYS` (à ajuster selon vos politiques).

## Roadmap / Idées futures

- Collecte de métriques Prometheus (`/metrics`).
- Catalogue de "handoffs" vers des outils CLI (ArchiveBox, theHarvester, etc.).
- UI graphique consommant `/graph`.
- Connecteurs facultatifs vers des coffres-forts de preuves.
