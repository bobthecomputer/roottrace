from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from roottrace.extraction.entities import EntityMatch


@dataclass(slots=True)
class Suggestion:
    """OSINT action recommendation."""

    tool: str
    command: str
    description: str
    category: str


def generate_suggestions(entities: Sequence[EntityMatch]) -> list[Suggestion]:
    """Produce OSINT suggestions based on extracted entities."""

    suggestions: list[Suggestion] = []
    domains = {entity.normalized or entity.value for entity in entities if entity.kind == "domain"}
    emails = {entity.normalized or entity.value for entity in entities if entity.kind == "email"}

    for domain in domains:
        suggestions.append(
            Suggestion(
                tool="subfinder",
                command=f"subfinder -d {domain} | dnsx -silent",
                description=(
                    "Enumérer les sous-domaines puis valider avec dnsx "
                    "(analyse réseau requise)."
                ),
                category="domain",
            )
        )
        suggestions.append(
            Suggestion(
                tool="crt.sh",
                command=f"https://crt.sh/?q=%25.{domain}",
                description="Inspecter les certificats publics associés au domaine.",
                category="domain",
            )
        )
        suggestions.append(
            Suggestion(
                tool="ArchiveBox",
                command=f"archivebox add https://{domain}",
                description="Archiver l'état actuel du domaine pour conservation légale.",
                category="preservation",
            )
        )

    for email in emails:
        suggestions.append(
            Suggestion(
                tool="theHarvester",
                command=f"theHarvester -d {email.split('@')[-1]} -l 200 -b all",
                description="Rechercher des traces publiques liées au domaine de l'adresse email.",
                category="email",
            )
        )
        suggestions.append(
            Suggestion(
                tool="EmailRep",
                command=f"emailrep {email}",
                description="Interroger EmailRep (API tierce, vérifier les CGU avant usage).",
                category="email",
            )
        )

    return suggestions


__all__ = ["Suggestion", "generate_suggestions"]
