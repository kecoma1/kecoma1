"""Update both stats cards with this calendar year's authenticated commit count."""

import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


def github_api(*arguments):
    result = subprocess.run(
        ["gh", "api", *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def update_card(path, year, count):
    namespace = "http://www.w3.org/2000/svg"
    ET.register_namespace("", namespace)
    tree = ET.parse(path)
    root = tree.getroot()
    value = root.find(f".//{{{namespace}}}text[@data-testid='commits']")
    if value is None:
        raise ValueError(f"Missing commit counter in {path.name}")

    row = next(parent for parent in root.iter() if value in list(parent))
    label = next(
        child for child in row
        if (child.text or "").strip().startswith(("Total Commits", "Commits ("))
    )
    label.text = f"Commits ({year}):"
    value.text = str(count)

    description = root.find(f"{{{namespace}}}desc")
    if description is not None and description.text:
        description.text, replacements = re.subn(
            r"(?:Total Commits|Commits)[^:]*:\s*[\d,.]+",
            f"Commits ({year}): {count}",
            description.text,
            count=1,
        )
        if replacements != 1:
            raise ValueError(f"Missing accessible commit description in {path.name}")

    path.write_text(ET.tostring(root, encoding="unicode") + "\n")


def main():
    today = datetime.now(timezone.utc).date()
    username = os.environ.get("GITHUB_REPOSITORY_OWNER") or github_api(
        "user", "--jq", ".login"
    )
    query = f"author:{username} author-date:{today.year}-01-01..{today.isoformat()}"
    result = json.loads(github_api(
        "--method", "GET", "search/commits",
        "-f", f"q={query}", "-f", "per_page=1",
        "--jq", "{total_count,incomplete_results}",
    ))
    if result.get("incomplete_results") or not isinstance(result.get("total_count"), int):
        raise ValueError("GitHub returned an incomplete commit count")

    count = result["total_count"]
    profile = Path(__file__).resolve().parents[2] / "profile"
    for mode in ("light", "dark"):
        update_card(profile / f"stats-{mode}.svg", today.year, count)
    print(f"Commits ({today.year}), public and private: {count:,}")


if __name__ == "__main__":
    main()
