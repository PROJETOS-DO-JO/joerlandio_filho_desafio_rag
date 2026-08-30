"""
Etapa 2 do fluxo: ler os documentos Markdown e dividi-los em chunks com metadados.

Estratégia adotada (documentada também no README):
  - O arquivo é dividido em "seções" a partir dos cabeçalhos Markdown (#, ##, ###...).
    Isso evita que um título fique separado da explicação que vem logo abaixo dele,
    porque o cabeçalho sempre permanece no início do texto da sua própria seção.
  - Dentro de cada seção, o texto é dividido em "blocos" respeitando a estrutura
    do Markdown: um bloco de código (```...```) é sempre um bloco inteiro e
    nunca é cortado no meio; um parágrafo de texto (entre linhas em branco) é
    outro tipo de bloco; e cada item de uma lista (* item / - item / 1. item)
    também vira seu próprio bloco, para nunca "colar" vários itens de lista
    numa única frase corrida. Os blocos são então agrupados em chunks de
    ~60-90 palavras (alvo: 75), unindo blocos com quebra de linha dupla
    (preservando a formatação original) em vez de "achatar" tudo numa linha só.
  - Overlap: o último bloco de um chunk é repetido como primeiro bloco do
    próximo chunk da mesma seção, para não perder contexto nas bordas.
  - Marcações de negrito/itálico do Markdown (**texto**, *texto*) são
    removidas do texto exibido, mesmo quando atravessam mais de uma linha —
    elas não ajudam a leitura de um trecho mostrado no terminal e só
    poluem o resultado. Marcadores de lista (*, +) são normalizados para
    "-". Nada disso é aplicado dentro de blocos de código, onde um "*" ou
    "**" costuma ser parte real do código (ex.: `2 * 3`, `**kwargs`).
  - Cada chunk carrega metadados suficientes para rastrear a origem:
    arquivo de origem, título do documento, seção e um id único do chunk.
"""
import re
from pathlib import Path

TARGET_WORDS = 75
OVERLAP_WORDS = 15
# Teto de segurança: um bloco isolado (ex.: um exemplo de código muito longo)
# maior que isso é quebrado por contagem de palavras, para nunca gerar um
# chunk gigantesco. Na prática isso raramente acontece na documentação do httpx.
MAX_BLOCK_WORDS = 150

# Tags HTML "cruas" que alguns arquivos da documentação embutem dentro do
# Markdown (ex.: <div align="center"><img .../><figcaption>...</figcaption></div>,
# usado para exibir imagens com legenda). Sem essa limpeza, o texto do chunk
# ficaria poluído com as tags literais (ex.: "div align center img src ...").
HTML_TAG_RE = re.compile(r"<\/?[a-zA-Z][^<>]*>")

# Marcações de ênfase do Markdown (negrito/itálico). Usa re.S porque um
# *itálico* às vezes atravessa mais de uma linha no texto original.
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)", re.S)
# Marcador de item de lista no início da linha ("* item" ou "+ item") é
# normalizado para "- item", removendo o asterisco sem perder a estrutura
# de lista.
BULLET_RE = re.compile(r"^(\s*)[*+](\s+)")
# Detecta se uma linha (já sem o marcador original) começa um novo item de
# lista, usado em split_into_blocks para nunca juntar dois itens numa única
# frase corrida.
LIST_ITEM_RE = re.compile(r"^(-|\d+\.)\s+")
# Divide um texto mantendo os blocos de código (```...``` ou ~~~...~~~)
# intactos como pedaços separados, para aplicar limpeza de Markdown só no
# texto normal e nunca dentro de código.
FENCE_SPLIT_RE = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", re.S)


def _strip_html_tags(line: str) -> str:
    cleaned = HTML_TAG_RE.sub(" ", line)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_bullet(line: str) -> str:
    return BULLET_RE.sub(lambda m: f"{m.group(1)}-{m.group(2)}", line)


def _strip_markdown_emphasis(text: str) -> str:
    """Remove marcações de negrito/itálico (**texto**, *texto*) de um texto,
    preservando qualquer trecho de código (```bloco``` ou `código em linha`)
    sem alterações — ali um "*"/"**" costuma ser parte real do código (ex.:
    `**kwargs`, `2 * 3`), não marcação de ênfase.

    Para não confundir os dois casos, todo trecho de código é primeiro
    substituído por um marcador temporário sem asteriscos (assim ele nunca
    "quebra" o pareamento de **negrito**/*itálico* ao redor dele, como em
    `*(Optional, with \`httpx[http2]\`)*`), e só depois é restaurado ao
    original.
    """
    protected = []

    def _protect(m):
        protected.append(m.group(0))
        return f"\x00{len(protected) - 1}\x00"

    placeholder_text = FENCE_SPLIT_RE.sub(_protect, text)
    placeholder_text = BOLD_RE.sub(r"\1", placeholder_text)
    placeholder_text = ITALIC_RE.sub(r"\1", placeholder_text)

    def _restore(m):
        return protected[int(m.group(1))]

    return re.sub(r"\x00(\d+)\x00", _restore, placeholder_text)


def split_into_sections(text: str):
    """Divide o texto do documento em seções por cabeçalho Markdown.

    Cada seção inclui a própria linha do cabeçalho + o corpo até o próximo
    cabeçalho, garantindo que título e explicação fiquem juntos.

    Importante: linhas dentro de blocos de código (```...```) são ignoradas
    na detecção de cabeçalhos. Sem isso, comentários como "# comentário"
    dentro de exemplos de código Python seriam confundidos com títulos
    Markdown, fragmentando o documento em seções minúsculas e sem sentido.
    Tags HTML fora de blocos de código são removidas linha a linha; a
    remoção de negrito/itálico é feita depois, texto inteiro da seção de
    uma vez (ver _strip_markdown_emphasis), para funcionar mesmo quando a
    marcação atravessa mais de uma linha.
    """
    lines = text.split("\n")
    cleaned_lines = []
    in_code_fence = False
    header_positions = []  # (linha, nível, texto do cabeçalho)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            cleaned_lines.append(line)
            continue
        if in_code_fence:
            cleaned_lines.append(line)
            continue

        cleaned_lines.append(_normalize_bullet(_strip_html_tags(line)))

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            header_positions.append((i, len(m.group(1)), m.group(2).strip()))

    if not header_positions:
        # Documento sem cabeçalhos (fora de blocos de código): uma única seção.
        body = _strip_markdown_emphasis("\n".join(cleaned_lines).strip())
        return [{"level": 0, "header": None, "text": body}]

    sections = []
    first_line = header_positions[0][0]
    if first_line > 0:
        preamble = "\n".join(cleaned_lines[:first_line]).strip()
        if preamble:
            sections.append({"level": 0, "header": None, "text": _strip_markdown_emphasis(preamble)})

    for idx, (line_idx, level, header) in enumerate(header_positions):
        start = line_idx
        end = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
        body = "\n".join(cleaned_lines[start:end]).strip()
        sections.append({"level": level, "header": header, "text": _strip_markdown_emphasis(body)})

    return sections


def split_into_blocks(text: str):
    """Divide o texto de uma seção em blocos "atômicos": um bloco de código
    (```...```) inteiro, um item de lista (* / - / 1.) com suas linhas de
    continuação, ou um parágrafo de texto comum (linhas entre quebras em
    branco). Cada bloco preserva suas quebras de linha internas — é isso que
    evita o problema de "achatar" tudo numa linha só e misturar cabeçalho,
    texto, itens de lista e código sem separação visual.
    """
    lines = text.split("\n")
    blocks = []
    current = []
    in_fence = False

    def flush():
        if current and any(l.strip() for l in current):
            blocks.append("\n".join(current).strip("\n"))
        current.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_fence:
                flush()
                current.append(line)
                in_fence = True
            else:
                current.append(line)
                flush()
                in_fence = False
            continue
        if in_fence:
            current.append(line)
            continue
        if stripped == "":
            flush()
            continue
        if LIST_ITEM_RE.match(stripped) and current:
            # Início de um novo item de lista: fecha o bloco anterior para
            # que cada item vire seu próprio bloco, em vez de todos ficarem
            # colados numa só frase corrida.
            flush()
        current.append(line)

    flush()
    return [b for b in blocks if b.strip()]


def chunk_words(text: str, target_words: int = TARGET_WORDS, overlap_words: int = OVERLAP_WORDS):
    """Fallback: divide um texto em blocos de ~target_words palavras com
    sobreposição, por contagem de palavras. Usado apenas quando um único
    bloco (ex.: um exemplo de código muito longo) sozinho já ultrapassa
    MAX_BLOCK_WORDS — caso raro na documentação do httpx."""
    words = text.split()
    if not words:
        return []
    if len(words) <= target_words:
        return [text.strip()]

    chunks = []
    step = max(1, target_words - overlap_words)
    start = 0
    while start < len(words):
        piece = words[start : start + target_words]
        chunks.append(" ".join(piece))
        if start + target_words >= len(words):
            break
        start += step
    return chunks


def group_blocks_into_chunks(blocks, target_words: int = TARGET_WORDS):
    """Agrupa blocos (parágrafos/itens de lista/código) em chunks de
    ~target_words palavras, unindo blocos com uma linha em branco
    (preservando formatação). Nunca corta um bloco no meio, a menos que ele
    sozinho ultrapasse MAX_BLOCK_WORDS (nesse caso, cai no fallback por
    palavras). O último bloco de um chunk é repetido como primeiro bloco do
    próximo, como sobreposição.
    """
    chunks = []
    current = []
    current_words = 0

    for block in blocks:
        block_words = len(block.split())

        if block_words > MAX_BLOCK_WORDS:
            if current:
                chunks.append("\n\n".join(current))
                current, current_words = [], 0
            chunks.extend(chunk_words(block))
            continue

        if current and current_words + block_words > target_words:
            chunks.append("\n\n".join(current))
            # sobreposição: o último bloco do chunk anterior reabre o próximo
            current = [current[-1]]
            current_words = len(current[0].split())

        current.append(block)
        current_words += block_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def build_chunks_for_file(file_path: Path, docs_root: Path):
    """Lê um arquivo .md, gera seções e devolve a lista de chunks com metadados."""
    file_path = Path(file_path)
    docs_root = Path(docs_root)
    rel_path = file_path.relative_to(docs_root)

    text = file_path.read_text(encoding="utf-8")
    sections = split_into_sections(text)

    doc_title = next((s["header"] for s in sections if s["level"] == 1), None)
    if not doc_title:
        doc_title = file_path.stem.replace("_", " ").title()

    chunks = []
    for sec_idx, sec in enumerate(sections):
        section_name = sec["header"] or doc_title
        blocks = split_into_blocks(sec["text"])
        pieces = group_blocks_into_chunks(blocks)
        for piece_idx, piece in enumerate(pieces):
            if not piece.strip():
                continue
            chunk_id = f"{rel_path.as_posix()}::sec{sec_idx}::chunk{piece_idx}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": piece.strip(),
                    "source_file": f"docs/{rel_path.as_posix()}",
                    "title": doc_title,
                    "section": section_name,
                }
            )
    return chunks
