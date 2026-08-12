"""Seed the database with all report templates — the single source of truth.

Every template is defined by a JSON file in the ``seeds/`` directory next to this
script (one file per template). Running this script (re)creates them all:

    python seed_data.py            # create missing / repair changed templates
    python seed_data.py --force    # same, but also overwrite user-edited content

Each seeds/*.json file has the shape::

    {
      "name": "...",
      "template_type": "...",
      "is_default": false,
      "description": "...",
      "content": <a JSON section-schema array, or a plain-text string>
    }

Templates are matched by name. By default an existing template's metadata
(type / default flag / description) is kept in sync and its content is filled in
only if it is missing or shorter than the seed (this repairs a truncated template
without clobbering deliberate edits). ``--force`` overwrites content unconditionally.
"""
import json
import sys
from pathlib import Path

from database.db import SessionLocal, init_db
from database.models import Template

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _content_to_str(content) -> str:
    """Seed content may be a JSON schema (list/dict) or legacy plain text."""
    if isinstance(content, str):
        return content
    return json.dumps(content)


def load_seed_templates():
    """Load every template definition from seeds/*.json, sorted by filename."""
    if not SEEDS_DIR.is_dir():
        raise FileNotFoundError(f"Seeds directory not found: {SEEDS_DIR}")
    templates = []
    for path in sorted(SEEDS_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["content"] = _content_to_str(data["content"])
        templates.append(data)
    return templates


def seed_templates(force: bool = False):
    """Create or update every template defined under seeds/."""
    init_db()
    db = SessionLocal()
    try:
        seeds = load_seed_templates()
        created = updated = unchanged = 0
        for seed in seeds:
            existing = db.query(Template).filter(Template.name == seed["name"]).first()
            if existing is None:
                db.add(Template(
                    name=seed["name"],
                    description=seed.get("description"),
                    template_type=seed["template_type"],
                    content=seed["content"],
                    is_default=seed.get("is_default", False),
                ))
                created += 1
                print(f"Created: {seed['name']}")
                continue

            # Keep metadata in sync; refresh content when forced, missing, or truncated.
            changed = False
            for attr in ("template_type", "description"):
                if seed.get(attr) is not None and getattr(existing, attr) != seed[attr]:
                    setattr(existing, attr, seed[attr]); changed = True
            if existing.is_default != seed.get("is_default", False):
                existing.is_default = seed.get("is_default", False); changed = True
            if force or not existing.content or len(existing.content) < len(seed["content"]):
                if existing.content != seed["content"]:
                    existing.content = seed["content"]; changed = True
            if changed:
                updated += 1
                print(f"Updated: {seed['name']}")
            else:
                unchanged += 1

        db.commit()
        print(f"\nDone. {created} created, {updated} updated, {unchanged} unchanged "
              f"({len(seeds)} templates total).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_templates(force="--force" in sys.argv)
