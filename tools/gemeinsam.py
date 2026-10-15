"""Gemeinsame Helfer für die zeugnis-kit Werkzeuge.

Nur Standardbibliothek. Kein pip install, keine zweite Datenhaltung.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

# Vokabular. Die Werte stehen in den JSONL-Dateien in ASCII; die Ampelsymbole
# setzt erst die Ausgabe (A-06), weil Register und Schreiben verschiedene
# Leser haben.
Q_STATUS = ("Q1", "Q2", "Q3", "Q4", "Q5")
AMPEL = ("gruen", "orange", "rot", "gruen-orange", "orange-rot", "unklar")
AMPEL_SYMBOL = {
    "gruen": "🟢",
    "orange": "🟠",
    "rot": "🔴",
    "gruen-orange": "🟢🟠",
    "orange-rot": "🟠🔴",
    "unklar": "⬜",
}
RECHTSSTATUS = (
    "korrekturanspruch-plausibel",
    "nur-verhandlung",
    "unklar-live-pruefen",
    "kein-handlungsbedarf",
)
KONFIDENZ = ("hoch", "mittel", "niedrig")
PRIO = ("A", "B", "C")
ACHSE = ("leistung", "verhalten", "engagement", "kompetenz")
SATZ_TYP = (
    "tatsache",
    "aufgabe",
    "leistung",
    "verhalten",
    "fuehrung",
    "schluss",
    "form",
)
ZEUGNISART = (
    "einfach",
    "qualifiziert",
    "zwischenzeugnis",
    "ausbildungszeugnis",
    "dienstzeugnis",
    "entwurf",
)

# Q4 ist Schlussfolgerung, Q5 ist ungeklärt. Keiner von beiden trägt eine
# Tatsache in ein Schreiben (Z-06).
Q_TRAEGT_KEINE_TATSACHE = ("Q4", "Q5")

# Nach Z-04 bekommt eine Aufgabenbeschreibung keine Note.
TYP_OHNE_NOTE = ("aufgabe", "form")

PFLICHT_SATZ = ("satz_id", "wortlaut", "quelle", "q_status", "typ")
PFLICHT_BEFUND = ("befund_id", "satz_ids", "prio", "gate_stufe", "begruendung")

NOTE = re.compile(r"[1-5]")
# Regelcodes dieses Kits (Z-04, A-01, P-07, M-02, F-03) und Katalogadressen des
# Upstreams (D.1, E.5, G.5). Sie tragen Ziffern, die keine Noten sind.
REGELCODE = re.compile(r"\b[ZAPMF]-\d+\b|\b[A-G]\.\d+\b|§+\s*\d+[\w\s.]*?(?:GewO|BGB|BBiG)")
# Ein Feld, das die Abwesenheit einer Note ausdrückt, trägt keine Note.
KEINE_NOTE = re.compile(r"\bkeine?\b|\bentfällt\b|\bentfaellt\b|^\s*[-–—]\s*$", re.I)


def heute() -> str:
    return date.today().isoformat()


def fehler(text: str, code: int = 2):
    print(f"FEHLER: {text}", file=sys.stderr)
    raise SystemExit(code)


def warnung(text: str):
    print(f"WARNUNG: {text}", file=sys.stderr)


def wurzel(start: Path | None = None) -> Path:
    """Findet den Arbeitsordner: der Ordner, der `faelle/` enthält."""
    p = (start or Path.cwd()).resolve()
    for kandidat in (p, *p.parents):
        if (kandidat / "faelle").is_dir():
            return kandidat
    fehler(
        "Kein Arbeitsordner gefunden. Erwartet wird ein Ordner mit `faelle/` "
        "oberhalb des Arbeitsverzeichnisses. Lege ihn mit der Skill `adopt` an."
    )


def jsonl_lesen(datei: Path) -> list[dict]:
    """Liest JSONL und meldet die Zeilennummer, wenn eine Zeile kaputt ist."""
    if not datei.is_file():
        return []
    saetze = []
    for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("//"):
            continue
        try:
            saetze.append(json.loads(zeile))
        except json.JSONDecodeError as e:
            fehler(f"{datei.name} Zeile {nr}: kein gültiges JSON — {e.msg}")
    return saetze


def faelle(w: Path) -> list[str]:
    return sorted(p.name for p in (w / "faelle").iterdir() if p.is_dir())


def fall_pfad(w: Path, fall: str) -> Path:
    p = w / "faelle" / fall
    if not p.is_dir():
        fehler(f"Fall `{fall}` gibt es nicht unter {w / 'faelle'}")
    return p


def register_lesen(w: Path, fall: str) -> list[dict]:
    return jsonl_lesen(fall_pfad(w, fall) / "register.jsonl")


def befunde_lesen(w: Path, fall: str) -> list[dict]:
    return jsonl_lesen(fall_pfad(w, fall) / "befunde.jsonl")


def satz_karte(register: list[dict]) -> dict[str, dict]:
    return {s["satz_id"]: s for s in register if "satz_id" in s}


def schreiben_lesen(w: Path, fall: str, name: str) -> str | None:
    p = fall_pfad(w, fall) / "schreiben" / f"{name}.md"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def abschnitte(text: str) -> list[tuple[int, str, str]]:
    """Zerlegt ein Schreiben in Abschnitte an Überschriften und Leerzeilen.

    Gibt (zeilennummer, ueberschrift, text) zurück. Der Abschnitt ist die
    Einheit, in der A-03 geprüft wird: eine Bitte darf nicht im selben
    Abschnitt stehen wie eine Frist.
    """
    zeilen = text.splitlines()
    blöcke: list[tuple[int, str, str]] = []
    aktuell: list[str] = []
    start = 1
    titel = ""
    for nr, z in enumerate(zeilen, 1):
        if z.startswith("#"):
            if aktuell:
                blöcke.append((start, titel, "\n".join(aktuell)))
            titel = z.lstrip("# ").strip()
            aktuell = []
            start = nr
            continue
        if not z.strip():
            if aktuell:
                blöcke.append((start, titel, "\n".join(aktuell)))
                aktuell = []
            continue
        if not aktuell:
            start = nr
        aktuell.append(z)
    if aktuell:
        blöcke.append((start, titel, "\n".join(aktuell)))
    return blöcke


def noten_menge(text: str) -> set[int]:
    """Zieht die Notenstufen aus einem Feld wie „3 bis 4" oder „2".

    Eine Spanne wird aufgefüllt: „3 bis 4" ergibt {3, 4}. Zusätze wie
    „mit Bereichsdrift" oder „/ lückenhaft" werden ignoriert — sie beschreiben
    den Befund, nicht den Korridor.

    Regelcodes werden vorher entfernt. Ein Agent, der die Abwesenheit einer
    Note begründet — `"keine (Z-04, Aufgabensatz)"` —, nennt dabei die Regel,
    und die trägt eine Ziffer. Ohne diesen Schnitt läse das Gate aus `Z-04`
    die Note 4 heraus und meldete genau den Agenten, der die Regel befolgt.
    """
    rest = REGELCODE.sub(" ", text)
    if KEINE_NOTE.search(rest):
        return set()
    treffer = [int(t) for t in NOTE.findall(rest)]
    if not treffer:
        return set()
    return set(range(min(treffer), max(treffer) + 1))


def tabellen(md: str) -> list[list[dict[str, str]]]:
    """Liest alle Markdown-Pipe-Tabellen eines Dokuments.

    Je Tabelle eine Liste von Zeilen-Dicts mit den Spaltenüberschriften als
    Schlüssel. Trennzeilen (`| --- |`) werden verworfen.
    """
    ergebnis: list[list[dict[str, str]]] = []
    kopf: list[str] | None = None
    zeilen: list[dict[str, str]] = []

    def feld(z: str) -> list[str]:
        return [t.strip() for t in z.strip().strip("|").split("|")]

    for z in md.splitlines():
        if z.lstrip().startswith("|"):
            werte = feld(z)
            if all(set(v) <= set("-: ") and v for v in werte):
                continue
            if kopf is None:
                kopf = werte
                continue
            zeilen.append(dict(zip(kopf, werte)))
        else:
            if kopf is not None and zeilen:
                ergebnis.append(zeilen)
            kopf, zeilen = None, []
    if kopf is not None and zeilen:
        ergebnis.append(zeilen)
    return ergebnis


def umfang(w: Path, geprueft: list[str]) -> list[str]:
    """Zeilen, die den Prüfumfang nennen — Pflichtkopf jedes Gate-Berichts.

    Ein Gate, das „ohne Befund" meldet, ohne zu sagen, was es angesehen hat,
    ist gefährlicher als keins: bei einem echten Mandat liest das jemand als
    grünes Licht. Das ist P-06 im eigenen Werkzeug, und der erste Lauf an
    echten Fällen hat genau das gezeigt — „Alle maschinell prüfbaren
    Bedingungen erfüllt" bei zweiundzwanzig nicht gelaufenen Fällen.
    """
    alle = faelle(w)
    offen = [f for f in alle if f not in geprueft]
    zeilen = [
        f"- Fälle im Arbeitsordner: {len(alle)}",
        f"- Davon geprüft: {len(geprueft)}" + (f" ({', '.join(geprueft)})" if geprueft else ""),
    ]
    if offen:
        zeilen.append(
            f"- **Nicht geprüft: {len(offen)}** — {', '.join(offen)}"
        )
    return zeilen


def nicht_geprueft_block(punkte: list[str]) -> list[str]:
    """Nennt ausdrücklich, was dieses Gate **nicht** abdeckt."""
    if not punkte:
        return []
    return ["", "## Von diesem Gate nicht geprüft", ""] + [f"- {p}" for p in punkte]


def bericht_schreiben(w: Path, name: str, zeilen: list[str]) -> Path:
    ziel = w / "gates" / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return ziel


class Befunde:
    """Sammelt Gate-Befunde mit Regelcode und gibt sie sortiert aus."""

    def __init__(self):
        self.liste: list[dict] = []

    def add(self, regel: str, fall: str, bezug: str, text: str):
        self.liste.append({"regel": regel, "fall": fall, "bezug": bezug, "text": text})

    def __len__(self):
        return len(self.liste)

    def __bool__(self):
        return bool(self.liste)

    def nach_regel(self) -> dict[str, list[dict]]:
        karte: dict[str, list[dict]] = {}
        for b in self.liste:
            karte.setdefault(b["regel"], []).append(b)
        return dict(sorted(karte.items()))

    def zeilen(self) -> list[str]:
        out: list[str] = []
        for regel, gruppe in self.nach_regel().items():
            out.append(f"\n## {regel} — {len(gruppe)}")
            out.append("")
            for b in gruppe:
                out.append(f"- `{b['fall']}` **{b['bezug']}** — {b['text']}")
        return out
