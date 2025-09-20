from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from roottrace.extraction.entities import EntityMatch
from roottrace.ingest.service import IngestService
from roottrace.osint.suggestions import generate_suggestions


class RootTraceController:
    """Coordinatrice pour l'UI desktop (ingestion + rendu)."""

    def __init__(self, service: IngestService | None = None) -> None:
        self.service = service or IngestService()

    def list_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        return [self._serialize_job(job) for job in self.service.list_recent_jobs(limit=limit)]

    def ingest_path(self, path: Path, source_uri: str | None = None) -> dict[str, Any]:
        job = self.service.ingest_path(path, source_uri=source_uri)
        stored = self.service.get_job(job.id)
        if stored is None:  # pragma: no cover - défense
            raise RuntimeError("Job introuvable après ingestion")
        return self._serialize_job(stored)

    def ingest_url(self, url: str) -> dict[str, Any]:
        job = self.service.ingest_url(url)
        stored = self.service.get_job(job.id)
        if stored is None:  # pragma: no cover - défense
            raise RuntimeError("Job introuvable après ingestion")
        return self._serialize_job(stored)

    def _serialize_job(self, job: Any) -> dict[str, Any]:
        matches = [
            EntityMatch(
                kind=entity.kind,
                value=entity.value,
                normalized=entity.normalized,
                context=entity.context,
                score=entity.score,
            )
            for entity in getattr(job, "entities", [])
        ]
        text_excerpt = (getattr(job, "text_content", "") or "")[:500] or None
        job_dict = {
            "id": job.id,
            "artifact_kind": job.artifact_kind.value,
            "content_type": job.content_type,
            "sha256": job.sha256,
            "size_bytes": job.size_bytes,
            "metadata": job.artifact_metadata,
            "summary": job.summary,
            "text_excerpt": text_excerpt,
        }
        entities = [
            {
                "kind": match.kind,
                "value": match.value,
                "normalized": match.normalized,
                "context": match.context,
                "score": match.score,
            }
            for match in matches
        ]
        suggestions = [asdict(suggestion) for suggestion in generate_suggestions(matches)]
        return {
            "job": job_dict,
            "entities": entities,
            "suggestions": suggestions,
        }


def run_app(controller: RootTraceController | None = None) -> None:  # pragma: no cover
    """Lancer l'interface Tkinter (bloquante)."""

    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    controller = controller or RootTraceController()

    root = tk.Tk()
    root.title("RootTrace Desktop")
    root.geometry("760x680")

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill=tk.BOTH, expand=True)

    title = tk.Label(frame, text="RootTrace Desktop", font=("Segoe UI", 18, "bold"))
    title.pack(anchor=tk.W, pady=(0, 8))

    subtitle = tk.Label(
        frame,
        text=(
            "Analyse locale d'artefacts. Sélectionnez un fichier ou indiquez une URL."
        ),
        justify=tk.LEFT,
    )
    subtitle.pack(anchor=tk.W, pady=(0, 16))

    result_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20)
    result_box.pack(fill=tk.BOTH, expand=True, pady=(16, 0))

    def _display_result(result: dict[str, Any]) -> None:
        job = result["job"]
        entities = result["entities"]
        suggestions = result["suggestions"]
        lines = [
            f"Job #{job['id']} · {job['artifact_kind'].upper()} · {job['content_type']}",
            f"SHA-256: {job['sha256']}",
            f"Taille: {job['size_bytes']} octets",
        ]
        if job.get("summary"):
            lines.append(f"Résumé: {job['summary']}")
        if job.get("text_excerpt"):
            lines.append("\nExtrait:\n" + job["text_excerpt"])
        if entities:
            lines.append("\nEntités:")
            for entity in entities:
                normalized = entity.get("normalized") or "—"
                lines.append(f"- {entity['kind']}: {entity['value']} (norm: {normalized})")
        if suggestions:
            lines.append("\nSuggestions OSINT:")
            for suggestion in suggestions:
                lines.append(f"- {suggestion['tool']}: {suggestion['command']}")
        result_box.delete("1.0", tk.END)
        result_box.insert(tk.END, "\n".join(lines))

    def _choose_file() -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        try:
            result = controller.ingest_path(Path(path))
        except Exception as exc:  # pragma: no cover - dépend GUI
            messagebox.showerror("Erreur", str(exc))
            return
        _display_result(result)

    url_frame = tk.Frame(frame)
    url_frame.pack(fill=tk.X, pady=(8, 0))

    url_label = tk.Label(url_frame, text="URL à analyser")
    url_label.pack(side=tk.LEFT)

    url_var = tk.StringVar()
    url_entry = tk.Entry(url_frame, textvariable=url_var)
    url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))

    def _ingest_url() -> None:
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("Attention", "Indiquez une URL valide.")
            return
        try:
            result = controller.ingest_url(url)
        except Exception as exc:  # pragma: no cover - dépend GUI
            messagebox.showerror("Erreur", str(exc))
            return
        _display_result(result)

    button_frame = tk.Frame(frame)
    button_frame.pack(fill=tk.X, pady=(8, 0))

    file_button = tk.Button(button_frame, text="Choisir un fichier", command=_choose_file)
    file_button.pack(side=tk.LEFT)

    url_button = tk.Button(button_frame, text="Analyser l'URL", command=_ingest_url)
    url_button.pack(side=tk.LEFT, padx=(8, 0))

    root.mainloop()


__all__ = ["RootTraceController", "run_app"]
