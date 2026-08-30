"""
Extra (fora do escopo obrigatório do desafio): converte o texto de um chunk
— que usa uma marcação Markdown simplificada (cabeçalhos, blocos de código,
código em linha, parágrafos) — em HTML seguro para exibição na interface
web (app.py), com blocos de código visualmente destacados em vez de
aparecerem como texto cru com ``` no meio.

Todo o conteúdo é escapado (html.escape) antes de virar HTML, então não há
risco de injeção mesmo vindo de texto de documentação externa.
"""
import html
import re

FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _render_inline_code(escaped_text: str) -> str:
    # escaped_text já passou por html.escape; o grupo capturado também já
    # está escapado, então não deve ser escapado de novo.
    return INLINE_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped_text)


def _render_text_segment(segment: str) -> list:
    out = []
    for block in segment.split("\n\n"):
        block = block.strip("\n")
        if not block.strip():
            continue
        header_m = HEADER_RE.match(block.strip())
        if header_m:
            level = min(len(header_m.group(1)) + 3, 6)
            content = _render_inline_code(html.escape(header_m.group(2).strip()))
            out.append(f"<h{level} class='chunk-heading'>{content}</h{level}>")
        else:
            escaped = html.escape(block).replace("\n", "<br>")
            escaped = _render_inline_code(escaped)
            out.append(f"<p class='chunk-p'>{escaped}</p>")
    return out


def render_chunk_html(text: str) -> str:
    """Converte o texto de um chunk em HTML: blocos ```código``` viram
    <pre><code>, cabeçalhos Markdown viram <hN>, `código em linha` vira
    <code>, e parágrafos normais viram <p>."""
    out = []
    last_end = 0
    for m in FENCE_RE.finditer(text):
        out.extend(_render_text_segment(text[last_end : m.start()]))
        lang = m.group(1)
        code = m.group(2).strip("\n")
        code_html = html.escape(code)
        lang_class = f' class="language-{html.escape(lang)}"' if lang else ""
        out.append(f'<pre class="chunk-code"><code{lang_class}>{code_html}</code></pre>')
        last_end = m.end()
    out.extend(_render_text_segment(text[last_end:]))
    return "\n".join(out)
