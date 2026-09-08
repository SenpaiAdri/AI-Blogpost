"""Repair model markdown: code fences, tables, title duplication, images."""

import html
import re
from typing import List

from generation.images import process_inline_images


def fix_code_blocks(content: str) -> str:
    """Fix malformed code blocks in markdown."""
    content = re.sub(r'\n(python)\n', r'\n```python\n', content)
    content = re.sub(r'\n(javascript)\n', r'\n```javascript\n', content)
    content = re.sub(r'\n(js)\n', r'\n```javascript\n', content)
    content = re.sub(r'\n(typescript)\n', r'\n```typescript\n', content)
    content = re.sub(r'\n(ts)\n', r'\n```typescript\n', content)
    content = re.sub(r'\n(bash)\n', r'\n```bash\n', content)
    content = re.sub(r'\n(shell)\n', r'\n```bash\n', content)
    content = re.sub(r'\n(json)\n', r'\n```json\n', content)
    content = re.sub(r'\n(sql)\n', r'\n```sql\n', content)
    content = re.sub(r'\n(html)\n', r'\n```html\n', content)
    content = re.sub(r'\n(css)\n', r'\n```css\n', content)
    content = re.sub(r'\n(java)\n', r'\n```java\n', content)
    content = re.sub(r'\n(c\+\+)\n', r'\n```cpp\n', content)
    content = re.sub(r'\n(cpp)\n', r'\n```cpp\n', content)
    content = re.sub(r'\n(rust)\n', r'\n```rust\n', content)
    content = re.sub(r'\n(go)\n', r'\n```go\n', content)
    content = re.sub(r'\n(golang)\n', r'\n```go\n', content)

    content = re.sub(r'\n```python\n\n', '\n```python\n', content)
    content = re.sub(r'\n```javascript\n\n', '\n```javascript\n', content)
    content = re.sub(r'\n```bash\n\n', '\n```bash\n', content)

    return content


_FENCE_LINE = re.compile(r"^\s*`{3}")
# Markdown bold word (not Python `x ** 2` with a digit right after **)
_MD_BOLD_WORD = re.compile(r"\*\*[A-Za-z_][^*\n]*\*\*")


def _line_signals_markdown_outside_fence(line: str) -> bool:
    """True when this line is almost certainly prose/markdown, not code."""
    s = line.strip()
    if s.startswith("!["):
        return True
    if _MD_BOLD_WORD.search(line):
        return True
    return False


def repair_leaked_markdown_fences(content: str) -> str:
    """Close a ``` fence before prose that was left inside a code block.

    Models often open ```python, paste real code, then continue the article without
    closing the fence and put a single ``` at the very end. That parses as one giant
    code block (headings and images stay literal). We insert an early closing fence
    before obvious markdown (images, **bold**), then drop a stray trailing ``` that
    used to close the oversized block.
    """
    if not content or "```" not in content:
        return content

    lines = content.split("\n")
    out: List[str] = []
    in_fence = False
    inserted_mid_close = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if _FENCE_LINE.match(line):
            rest = stripped[3:].strip() if len(stripped) >= 3 else ""
            if in_fence:
                in_fence = False
                out.append(line)
                i += 1
                continue
            in_fence = True
            out.append(line)
            i += 1
            continue

        if in_fence and _line_signals_markdown_outside_fence(line):
            out.append("```")
            out.append("")
            in_fence = False
            inserted_mid_close = True
            continue

        out.append(line)
        i += 1

    result = "\n".join(out)
    if inserted_mid_close:
        result = result.rstrip("\n")
        tail_lines = result.split("\n")
        while tail_lines and tail_lines[-1].strip() == "":
            tail_lines.pop()
        if tail_lines and tail_lines[-1].strip() == "```":
            tail_lines.pop()
            result = "\n".join(tail_lines)
            if result and not result.endswith("\n"):
                result += "\n"
    return result


def normalize_markdown_fences(content: str) -> str:
    """Repair prose leaked inside fences, then balance odd ``` counts."""
    content = repair_leaked_markdown_fences(content)
    content = balance_markdown_fences(content)
    return content


def balance_markdown_fences(content: str) -> str:
    """If markdown has an odd number of ``` fence lines, append a closing fence.

    Models sometimes omit the closing fence, which makes the rest of the article
    parse as one code block (images and headings never render as HTML).
    """
    if not content:
        return content
    lines = content.splitlines()
    fence_lines = sum(1 for line in lines if _FENCE_LINE.match(line))
    if fence_lines % 2 == 1:
        if not content.endswith("\n"):
            content += "\n"
        content += "```\n"
    return content


def fix_tables(content: str) -> str:
    """Fix markdown table separators for likely table blocks only."""
    lines = content.split("\n")
    fixed_lines = []

    def _pipe_count(text: str) -> int:
        return text.count("|")

    def _is_probable_table_header(text: str) -> bool:
        s = text.strip()
        if not s or s.startswith("```"):
            return False
        # Avoid rewriting obvious prose/sentences that include pipes.
        if s.startswith("- ") or s.startswith("* ") or s.startswith(">"):
            return False
        return _pipe_count(text) >= 2

    def _is_table_separator(text: str) -> bool:
        return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", text))

    def _normalize_table_row(text: str, expected_cols: int) -> str:
        s = text.strip()
        if not s.startswith("|"):
            s = "| " + s
        if not s.endswith("|"):
            s = s + " |"
        col_count = _pipe_count(s) - 1
        if col_count < expected_cols:
            s = s[:-1] + (" |" * (expected_cols - col_count)) + "|"
        return s

    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if _FENCE_LINE.match(line):
            in_fence = not in_fence
            fixed_lines.append(line)
            i += 1
            continue

        # Only treat as a table when we can confirm a minimum shape:
        # header row + at least one more pipe row.
        if (not in_fence) and _is_probable_table_header(line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if _pipe_count(next_line) >= 2:
                header_line = _normalize_table_row(line, _pipe_count(line) - 1)

                if _is_table_separator(next_line):
                    sep_line = _normalize_table_row(next_line, _pipe_count(header_line) - 1)
                    row_start = i + 2
                else:
                    cols = max(_pipe_count(header_line) - 1, 1)
                    sep_line = "| " + " | ".join(["---"] * cols) + " |"
                    row_start = i + 1

                # Require at least one body row to avoid false positives on prose.
                if row_start < len(lines) and _pipe_count(lines[row_start]) >= 2:
                    fixed_lines.append(header_line)
                    fixed_lines.append(sep_line)
                    i = row_start
                    while i < len(lines) and _pipe_count(lines[i]) >= 2:
                        fixed_lines.append(
                            _normalize_table_row(lines[i], _pipe_count(header_line) - 1)
                        )
                        i += 1
                    continue

            fixed_lines.append(line)
            i += 1
        else:
            fixed_lines.append(line)
            i += 1

    return "\n".join(fixed_lines)


def sanitize_ai_content(
    title: str,
    content: str,
    source_name: str = "",
    source_url: str = "",
) -> str:
    """Sanitize AI-generated content to fix common issues."""
    content = html.unescape(content)

    content = re.sub(r'^#+\s*' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)

    content = re.sub(r'^' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)

    title_words = title.lower().split()
    if len(title_words) >= 3:
        first_3 = ' '.join(title_words[:3])
        content = re.sub(r'^#+\s*' + re.escape(first_3) + r'\s*$', '', content, flags=re.MULTILINE)

    content = fix_code_blocks(content)

    content = normalize_markdown_fences(content)

    content = fix_tables(content)

    content = re.sub(r'\n{3,}', '\n\n', content)

    content = re.sub(r' +$', '', content, flags=re.MULTILINE)

    content = content.strip()

    content = process_inline_images(content, source_name, source_url)

    return content
