"""
Script principal da fase de PREPARAÇÃO do RAG:

    repositório -> arquivos Markdown -> chunks + metadados -> embeddings -> índice salvo

Rode este script uma única vez (ou sempre que quiser reconstruir o índice):

    python build_index.py

Ele vai:
  1. Clonar (ou reaproveitar) o repositório httpx no commit fixado pelo desafio.
  2. Encontrar recursivamente os arquivos .md em httpx_repo/docs/.
  3. Ler e dividir cada arquivo em chunks com metadados (arquivo, título, seção).
  4. Calcular embeddings para todos os chunks.
  5. Salvar o índice (embeddings + metadados) na pasta index/, para reuso rápido
     em consultas futuras sem precisar recalcular tudo de novo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.chunking import build_chunks_for_file
from src.fetch_docs import ensure_httpx_repo, find_markdown_files
from src.indexer import RAGIndex

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR / "httpx_repo"
DOCS_DIR = REPO_DIR / "docs"
INDEX_DIR = BASE_DIR / "index"


def main():
    print("=== Fase 1: obtendo a base documental ===")
    ensure_httpx_repo(REPO_DIR)

    md_files = find_markdown_files(DOCS_DIR)
    print(f"Encontrados {len(md_files)} arquivos .md em {DOCS_DIR}")
    if len(md_files) != 23:
        print(
            "Aviso: a contagem esperada para o commit fixado é 23. "
            "Verifique se o checkout foi feito corretamente."
        )

    if not md_files:
        raise SystemExit(
            "Nenhum arquivo Markdown encontrado (corpus vazio). "
            "Não é possível construir o índice sem documentos."
        )

    print("\n=== Fase 2: lendo documentos e criando chunks com metadados ===")
    all_chunks = []
    for f in md_files:
        all_chunks.extend(build_chunks_for_file(f, DOCS_DIR))
    print(f"Total de chunks gerados: {len(all_chunks)} (a partir de {len(md_files)} arquivos)")

    print("\n=== Fase 3: calculando embeddings e salvando o índice ===")
    index = RAGIndex()
    index.build(all_chunks)
    index.save(INDEX_DIR)

    print("\nPronto! Agora rode: python query.py \"sua pergunta aqui\"")


if __name__ == "__main__":
    main()
