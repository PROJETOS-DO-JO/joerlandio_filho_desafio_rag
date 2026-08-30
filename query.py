"""
Script principal da fase de CONSULTA do RAG.

Recebe uma pergunta sem exigir alteração de código-fonte (via argumento de
linha de comando ou modo interativo) e devolve os trechos mais relevantes
da documentação do HTTPX, com suas fontes.

Uso:
    python query.py "Como fazer uma requisição GET com httpx?"
    python query.py "Como configurar timeout?" --top-k 5
    python query.py "Como configurar timeout?" --generate     (extensão opcional, usa Gemini)
    python query.py                                            (modo interativo)
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.indexer import RAGIndex

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"

# Linha de marcação de bloco de código Markdown (``` ou ```python, ~~~...).
FENCE_LINE_RE = re.compile(r"^\s*(```|~~~)\S*\s*$")


def _strip_fence_markers(text: str) -> str:
    """Remove só as LINHAS de marcação de bloco de código (``` / ```python)
    para exibição no terminal. O terminal não interpreta Markdown, então
    esses marcadores aparecem como texto cru, poluindo o trecho mostrado —
    o código em si continua exibido normalmente, só a linha da marcação some.

    Isso é puramente cosmético: o texto original do chunk (com as marcações
    intactas) continua sendo usado na busca e na geração da resposta em
    português, e no demo_output.md — lá as marcações são necessárias, pois
    é um arquivo Markdown de verdade e elas fazem o código renderizar
    corretamente com destaque de sintaxe.
    """
    lines = text.split("\n")
    return "\n".join(line for line in lines if not FENCE_LINE_RE.match(line))


def format_results(results):
    lines = []
    for r in results:
        display_text = _strip_fence_markers(r["text"])
        lines.append(
            f"[{r['rank']}] score={r['score']:.4f} | fonte={r['source_file']} | "
            f"título/seção: {r['title']} / {r['section']}\n"
            f"    \"{display_text}\""
        )
    return "\n\n".join(lines)


def run_query(index: RAGIndex, question: str, top_k: int = 3, generate: bool = False):
    try:
        results = index.search(question, top_k=top_k)
    except ValueError as e:
        # Tratamento explícito: pergunta vazia, corpus vazio ou top_k inválido
        # geram uma mensagem compreensível em vez de um traceback.
        print(f"Não foi possível concluir a busca: {e}")
        return None

    print(f"\nPergunta: {question}")
    print(f"Top {len(results)} resultado(s):\n")
    print(format_results(results))

    if generate:
        from src.generate import generate_answer

        answer = generate_answer(question, results)
        print_highlighted_answer(answer)

    return results


def print_highlighted_answer(answer: str):
    """Imprime a resposta gerada (em português) destacada visualmente, para
    diferenciar claramente dos trechos em inglês recuperados acima. Os
    trechos em inglês continuam sendo exibidos normalmente — eles são
    obrigatórios (mostram a fonte exata da documentação) e não são removidos."""
    is_fallback = answer.strip().startswith("[Geração")
    label = "AVISO DA GERAÇÃO (extensão opcional)" if is_fallback else "RESPOSTA EM PORTUGUÊS (gerada via Gemini)"
    border = "=" * 70
    print(f"\n{border}")
    print(f" {label}")
    print(border)
    print(answer)
    print(f"{border}\n")


def main():
    parser = argparse.ArgumentParser(description="Consulta o núcleo de recuperação do RAG-HTTPX.")
    parser.add_argument("question", nargs="?", default=None, help="Pergunta a ser feita (opcional)")
    parser.add_argument("--top-k", type=int, default=3, help="Número de resultados, entre 3 e 5 (padrão: 3)")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Gera uma resposta em linguagem natural com a Gemini API (extensão opcional)",
    )
    args = parser.parse_args()

    try:
        index = RAGIndex.load(INDEX_DIR)
    except FileNotFoundError as e:
        raise SystemExit(f"{e}")

    if args.question is not None:
        run_query(index, args.question, top_k=args.top_k, generate=args.generate)
        return

    print("Modo interativo. Digite sua pergunta (ou 'sair' para encerrar).")
    while True:
        try:
            question = input("\nPergunta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break
        if question.lower() in {"sair", "exit", "quit"}:
            break
        run_query(index, question, top_k=args.top_k, generate=args.generate)


if __name__ == "__main__":
    main()
