"""Add entries to CHANGELOG.md under the [Unreleased] section.

This CLI enforces a uniform Keep a Changelog style and preserves SemVer notes.
It ensures an `## [Unreleased]` section exists at the top, creates or finds
the requested category subsection (e.g., "Added", "Fixed"), and appends a new
bullet. Unknown subsections are preserved. Duplicate bullets are not added.

References:
- Keep a Changelog 1.1.0: https://keepachangelog.com/en/1.1.0/
- Semantic Versioning 2.0.0: https://semver.org/

Example:
    python scripts/cl_add.py -s Added -e "Add CLI for changelog updates"
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


# Ordered, canonical subsections
SECTIONS_ORDER: list[str] = [
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Breaking Changes",
    "Notes",
]

# Aliases -> canonical section names (case-insensitive; punctuation-insensitive)
SECTION_ALIASES: dict[str, str] = {
    "add": "Added",
    "added": "Added",
    "change": "Changed",
    "changed": "Changed",
    "deprecate": "Deprecated",
    "deprecated": "Deprecated",
    "remove": "Removed",
    "removed": "Removed",
    "fix": "Fixed",
    "fixed": "Fixed",
    "security": "Security",
    "breaking": "Breaking Changes",
    "breaking change": "Breaking Changes",
    "breaking changes": "Breaking Changes",
    "notes": "Notes",
    "note": "Notes",
}


@dataclass
class CategoryBlock:
    """Container for a parsed category block within [Unreleased].

    Attributes:
        heading: Canonical or original heading text for the category.
        body: Raw body string under the heading, excluding the heading line.
        bullets: A set of normalized bullet texts for duplicate detection.
    """

    heading: str
    body: str
    bullets: set[str]


_LOGGER = logging.getLogger("cl_add")
_HEADING_H1_RE = re.compile(r"(?m)^\s*#\s+.+?$")
_HEADING_H2_RE = re.compile(r"(?m)^\s*##\s+\[.+?\].*?$")
_CAT_HEADING_RE = re.compile(r"(?m)^\s*###\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"(?m)^\s*-\s+(.+?)\s*$")


def canonicalize_section(name: str) -> str:
    """Return the canonical section name for a user-supplied string.

    Args:
        name: Section name from CLI input.

    Returns:
        Canonical section string as defined in SECTIONS_ORDER.

    Raises:
        ValueError: If the name cannot be mapped to a known section.
    """
    key = re.sub(r"[\s_-]+", " ", name.strip().lower())
    key = key.rstrip("s") if key not in SECTION_ALIASES else key
    mapped = SECTION_ALIASES.get(key)
    if mapped:
        return mapped
    # Try exact title-case match as a last resort
    if name.strip() in SECTIONS_ORDER:
        return name.strip()
    raise ValueError(f"Unknown section: {name!r}")


def find_repo_root() -> Path:
    """Return the repository root using git, or cwd if git is unavailable.

    Returns:
        Path to repo root or current working directory.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def _normalize_for_compare(text: str) -> str:
    """Normalize bullet text for duplicate detection.

    Args:
        text: Bullet text.

    Returns:
        Canonicalized string for case/space/punctuation-insensitive compare.
    """
    core = re.sub(r"\s+", " ", text).strip()
    core = core.rstrip(" .;:,")
    return core.lower()


def _ensure_header_prefix(content: str) -> str:
    """Ensure the file begins with a standard header.

    Args:
        content: Existing file content (possibly empty).

    Returns:
        Content with a header if it was missing.
    """
    if not content.strip():
        return (
            "# Changelog\n\n"
            "All notable changes to this project are documented in this file.\n\n"
            "The format is based on Keep a Changelog 1.1.0 and the project\n"
            "adheres to Semantic Versioning 2.0.0.\n\n"
        )
    if not _HEADING_H1_RE.search(content.splitlines()[0]):
        # Prepend a header if the very first line is not an H1
        return f"# Changelog\n\n{content}"
    return content


def _find_unreleased_span(text: str) -> tuple[int, int] | None:
    """Find the byte-span of the `## [Unreleased]` block.

    Args:
        text: Full changelog text.

    Returns:
        (start, end) indices of the block, or None if not present.
    """
    m = re.search(r"(?m)^\s*##\s+\[Unreleased\].*?$", text)
    if not m:
        return None
    start = m.start()
    next_h2 = _HEADING_H2_RE.search(text, pos=m.end())
    end = next_h2.start() if next_h2 else len(text)
    return (start, end)


def _extract_unreleased(text: str) -> tuple[str, int, int]:
    """Return unreleased block text and its (start, end) span.

    If absent, an empty block text is returned with start=end=-1.

    Args:
        text: Full changelog text.

    Returns:
        Tuple of (block_text, start, end).
    """
    span = _find_unreleased_span(text)
    if not span:
        return ("", -1, -1)
    start, end = span
    return (text[start:end], start, end)


def _parse_categories(
    unrel_block: str,
) -> tuple[str, dict[str, CategoryBlock], list[tuple[str, str]]]:
    """Parse categories from an Unreleased block.

    Args:
        unrel_block: Text of the `## [Unreleased]` block (including its H2).

    Returns:
        A tuple of:
            - preamble text before the first category (may be empty)
            - dict of recognized CategoryBlock keyed by canonical section
            - list of unknown categories as (original_heading, body)
    """
    # Remove the H2 heading line
    lines = unrel_block.splitlines(keepends=True)
    if lines and lines[0].lstrip().startswith("## [Unreleased]"):
        body_text = "".join(lines[1:]).lstrip("\n")
    else:
        body_text = unrel_block

    recognized: dict[str, CategoryBlock] = {}
    unknown: list[tuple[str, str]] = []

    # Split by category headings
    segments: list[tuple[str, str]] = []
    last_idx = 0
    for m in _CAT_HEADING_RE.finditer(body_text):
        if m.start() > last_idx:
            # Text before this category
            if last_idx == 0 and m.start() > 0:
                preamble = body_text[last_idx : m.start()]
            else:
                preamble = ""
            segments.append(("", preamble))
        heading = m.group(1).strip()
        # Find next heading to slice the body
        next_m = _CAT_HEADING_RE.search(body_text, pos=m.end())
        end = next_m.start() if next_m else len(body_text)
        seg_body = body_text[m.end() : end]
        segments.append((heading, seg_body))
        last_idx = end

    if not segments:
        # No category headings at all
        return (body_text, recognized, unknown)

    # There may be trailing text after the last category heading
    tail = body_text[last_idx:]
    if tail:
        segments.append(("", tail))

    preamble_accum = []
    for head, seg_body in segments:
        if not head:
            preamble_accum.append(seg_body)
            continue
        try:
            canonical = canonicalize_section(head)
            bullets = {
                _normalize_for_compare(m.group(1))
                for m in _BULLET_RE.finditer(seg_body)
            }
            recognized[canonical] = CategoryBlock(
                heading=canonical, body=seg_body, bullets=bullets
            )
        except ValueError:
            unknown.append((head, seg_body))

    preamble_text = "".join(preamble_accum).strip("\n")
    return (preamble_text, recognized, unknown)


def _render_unreleased(
    preamble: str,
    recognized: dict[str, CategoryBlock],
    unknown: list[tuple[str, str]],
) -> str:
    """Render a normalized `## [Unreleased]` block.

    Args:
        preamble: Preamble text before categories.
        recognized: Canonical categories and bodies.
        unknown: Unknown categories to preserve, in original form.

    Returns:
        A complete `## [Unreleased]` block string.
    """
    parts: list[str] = []
    parts.append("## [Unreleased]\n\n")
    if preamble.strip():
        parts.append(preamble.rstrip() + "\n\n")

    # Render canonical categories in fixed order
    for name in SECTIONS_ORDER:
        block = recognized.get(name)
        if not block:
            continue
        parts.append(f"### {name}\n")
        body = block.body.lstrip("\n")
        # Ensure a trailing newline
        if not body.endswith("\n"):
            body += "\n"
        parts.append(body + "\n")

    # Preserve unknown categories after recognized ones
    for original, body in unknown:
        parts.append(f"### {original}\n")
        body2 = body.lstrip("\n")
        if not body2.endswith("\n"):
            body2 += "\n"
        parts.append(body2 + "\n")

    # Guarantee a single trailing newline
    return "".join(parts).rstrip() + "\n"


def _ensure_unreleased_at_top(full_text: str, new_unrel: str) -> str:
    """Place the given Unreleased block right after the file header.

    Args:
        full_text: Entire changelog content.
        new_unrel: Rendered `## [Unreleased]` block.

    Returns:
        Updated full content with Unreleased block at the top.
    """
    # Remove any existing Unreleased block
    _, start, end = _extract_unreleased(full_text)
    if start != -1:
        full_text = full_text[:start] + full_text[end:]

    # Find first H2 or end of header to insert after
    m_h2 = _HEADING_H2_RE.search(full_text)
    if m_h2 and _HEADING_H1_RE.search(full_text[: m_h2.start()]):
        header_end = m_h2.start()
    else:
        # Insert after the H1 header or at the beginning if none
        m_h1 = _HEADING_H1_RE.search(full_text)
        header_end = m_h1.end() if m_h1 else 0

    before = full_text[:header_end].rstrip() + "\n\n"
    after = full_text[header_end:].lstrip("\n")
    return before + new_unrel + "\n" + after


def _append_bullet_to_block(block_body: str, bullet: str) -> str:
    """Append a bullet line to a category body.

    Args:
        block_body: Existing body text under a category heading.
        bullet: Bullet text to append (without leading '- ').

    Returns:
        Updated body text with the new bullet appended.
    """
    block_body = block_body.rstrip() + "\n"
    if block_body and not block_body.endswith("\n"):
        block_body += "\n"
    return block_body + f"- {bullet}\n"


def update_changelog(
    changelog_path: Path, section: str, entries: Iterable[str]
) -> bool:
    """Add one or more bullets under `## [Unreleased]` and the given section.

    Args:
        changelog_path: Path to CHANGELOG.md.
        section: Canonical or alias section name.
        entries: One or more bullet texts.

    Returns:
        True if the file was modified, False if no change was required.

    Raises:
        FileNotFoundError: If the path exists but is not a file.
        UnicodeDecodeError: If the file encoding cannot be read as UTF-8.
        ValueError: For an unknown section name.
        PermissionError: If the path is not writable.
    """
    canonical = canonicalize_section(section)
    if changelog_path.exists() and not changelog_path.is_file():
        raise FileNotFoundError(f"Not a file: {changelog_path}")

    original = ""
    if changelog_path.exists():
        original = changelog_path.read_text(encoding="utf-8")
    original = _ensure_header_prefix(original)

    # Ensure an Unreleased block exists
    block_text, start, _end = _extract_unreleased(original)
    if start == -1:
        block_text = "## [Unreleased]\n\n"
    preamble, recognized, unknown = _parse_categories(block_text)

    # Ensure target category exists
    target = recognized.get(canonical)
    if not target:
        target = CategoryBlock(heading=canonical, body="", bullets=set())
        recognized[canonical] = target

    changed = False
    for entry in entries:
        entry_txt = entry.strip()
        if entry_txt.startswith("- "):
            entry_txt = entry_txt[2:].strip()
        key = _normalize_for_compare(entry_txt)
        if key in target.bullets:
            _LOGGER.info("Duplicate bullet ignored in %s: %s", canonical, entry_txt)
            continue
        target.body = _append_bullet_to_block(target.body, entry_txt)
        target.bullets.add(key)
        changed = True

    # Render new Unreleased block with canonical ordering
    new_unrel = _render_unreleased(preamble, recognized, unknown)

    # Ensure Unreleased is at the top
    updated = _ensure_unreleased_at_top(original, new_unrel)

    if updated == original:
        return False

    # Write back
    changelog_path.write_text(updated, encoding="utf-8")
    return changed


def run(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional list of CLI arguments.

    Returns:
        Zero on success, non-zero on failure.
    """
    parser = argparse.ArgumentParser(
        prog="cl_add",
        description=(
            "Add a bullet to CHANGELOG.md under ## [Unreleased] and the chosen section."
        ),
    )
    parser.add_argument(
        "-s",
        "--section",
        required=True,
        help=(
            "Target section. One of: "
            + ", ".join(SECTIONS_ORDER)
            + ". Aliases allowed."
        ),
    )
    parser.add_argument(
        "-e",
        "--entry",
        action="append",
        required=True,
        help="Bullet text to add. Repeat for multiple bullets.",
    )
    parser.add_argument(
        "-f",
        "--file",
        default="CHANGELOG.md",
        help="Path to the changelog file. Defaults to project root CHANGELOG.md.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        repo_root = find_repo_root()
        path = Path(args.file)
        if not path.is_absolute():
            path = repo_root / path
        _LOGGER.info("Using changelog: %s", path)
        changed = update_changelog(path, args.section, args.entry)
        if changed:
            _LOGGER.info("Changelog updated.")
        else:
            _LOGGER.info("No changes needed.")
        return 0
    except UnicodeDecodeError:
        _LOGGER.exception("Encoding error reading file")
        return 2
    except ValueError:
        _LOGGER.exception("ValueError occurred")
        return 3
    except FileNotFoundError:
        _LOGGER.exception("File not found")
        return 4
    except PermissionError:
        _LOGGER.exception("Permission error")
        return 5


if __name__ == "__main__":
    raise SystemExit(run())
