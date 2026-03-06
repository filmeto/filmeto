"""Markdown parser for splitting text into renderable segments.

Splits markdown text containing fenced code blocks into alternating
text and code_block segments. Text segments retain inline markdown
(bold, italic, headers, lists, links) for QML MarkdownText rendering.
Code blocks are extracted for dedicated CodeBlockWidget rendering.

Designed for streaming: unclosed code fences are treated as plain text,
so partial streaming content renders correctly without visual jumps.
"""
import re
from typing import List, Dict, Any

_CODE_FENCE_OPEN_RE = re.compile(r'^(`{3,}|~{3,})([\w+#.-]*)\s*$')


def parse_markdown_blocks(text: str) -> List[Dict[str, Any]]:
    """Split markdown text into text and code_block segments.

    Args:
        text: Raw markdown text potentially containing fenced code blocks.

    Returns:
        List of segment dicts:
          - {"type": "text", "text": "..."} for markdown text
          - {"type": "code_block", "code": "...", "language": "..."} for code
    """
    if not text:
        return []

    if '```' not in text and '~~~' not in text:
        return [{"type": "text", "text": text}]

    lines = text.split('\n')
    segments: List[Dict[str, Any]] = []
    text_buf: List[str] = []
    code_buf: List[str] = []
    in_code = False
    fence_marker = ""
    code_lang = ""

    for line in lines:
        if not in_code:
            m = _CODE_FENCE_OPEN_RE.match(line)
            if m:
                _flush_text(text_buf, segments)
                text_buf = []
                in_code = True
                fence_marker = m.group(1)
                code_lang = m.group(2) or "text"
                code_buf = []
            else:
                text_buf.append(line)
        else:
            stripped = line.strip()
            if stripped == fence_marker or (
                stripped.startswith(fence_marker[0] * len(fence_marker))
                and stripped == fence_marker[0] * len(stripped)
                and len(stripped) >= len(fence_marker)
            ):
                in_code = False
                segments.append({
                    "type": "code_block",
                    "code": '\n'.join(code_buf),
                    "language": code_lang,
                })
                code_buf = []
            else:
                code_buf.append(line)

    if in_code:
        text_buf.append(fence_marker + code_lang)
        text_buf.extend(code_buf)

    _flush_text(text_buf, segments)

    return segments if segments else [{"type": "text", "text": text}]


def _flush_text(buf: List[str], segments: List[Dict[str, Any]]) -> None:
    if not buf:
        return
    t = '\n'.join(buf).strip()
    if t:
        segments.append({"type": "text", "text": t})


def has_markdown_code_blocks(text: str) -> bool:
    """Fast check for fenced code blocks without full parsing."""
    if not text:
        return False
    idx = text.find('```')
    if idx == -1:
        idx = text.find('~~~')
    if idx == -1:
        return False
    rest = text[idx + 3:]
    return '```' in rest or '~~~' in rest
