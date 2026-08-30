"""
Extensão opcional: teste automatizado da mecânica do pipeline (chunking,
metadados, persistência do índice, busca e tratamento de erros).

Por que um embedding "falso"? Rodar este teste com o modelo real de
embeddings baixaria ~500MB e exigiria internet só para validar lógica que
não depende de semântica (alinhamento de índices, formato dos resultados,
mensagens de erro). Por isso o modelo é substituído por um embedding
determinístico simples (hash de palavras), rápido e sem dependências extras.
A qualidade semântica de verdade é validada manualmente com o modelo real
em query.py / demo_perguntas.py (veja o README).

Uso:
    python tests/test_pipeline.py
"""
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.chunking import MAX_BLOCK_WORDS, build_chunks_for_file
from src.fetch_docs import ensure_httpx_repo, find_markdown_files
from src.indexer import RAGIndex

REPO_DIR = BASE_DIR / "httpx_repo"
DOCS_DIR = REPO_DIR / "docs"

DIM = 64


def fake_embed(text: str) -> np.ndarray:
    vec = np.zeros(DIM, dtype="float32")
    for word in text.lower().split():
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        vec[h % DIM] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


class FakeModel:
    def encode(self, texts, **kwargs):
        return np.stack([fake_embed(t) for t in texts])


class FakeRAGIndex(RAGIndex):
    """Mesma lógica de RAGIndex, mas com um encoder falso (sem baixar modelo)."""

    @property
    def model(self):
        if self._model is None:
            self._model = FakeModel()
        return self._model


def main():
    ensure_httpx_repo(REPO_DIR)

    print("1) find_markdown_files + chunking em documentos reais do httpx...")
    md_files = find_markdown_files(DOCS_DIR)
    assert len(md_files) == 23, f"esperado 23 arquivos .md, encontrado {len(md_files)}"
    print(f"   OK: {len(md_files)} arquivos .md")

    all_chunks = []
    for f in md_files:
        all_chunks.extend(build_chunks_for_file(f, DOCS_DIR))
    assert len(all_chunks) > 0
    lens = [len(c["text"].split()) for c in all_chunks]
    # 75 é só o ALVO de agrupamento (chunks costumam ficar perto disso); o
    # teto de segurança de verdade é MAX_BLOCK_WORDS (150), usado só quando
    # um único bloco isolado — ex.: um exemplo de código longo — já
    # ultrapassa esse valor sozinho.
    assert max(lens) <= MAX_BLOCK_WORDS, "chunk excedeu o teto de segurança de palavras"
    ids = [c["chunk_id"] for c in all_chunks]
    assert len(ids) == len(set(ids)), "chunk_id duplicado"
    for c in all_chunks[:3]:
        assert {"chunk_id", "text", "source_file", "title", "section"} <= set(c.keys())
    print(f"   OK: {len(all_chunks)} chunks, metadados presentes, ids únicos")

    print("\n2) build + save + load do índice (embedding falso, sem baixar modelo)...")
    with tempfile.TemporaryDirectory() as tmp:
        idx = FakeRAGIndex()
        idx.build(all_chunks)
        idx.save(tmp)
        idx2 = FakeRAGIndex.load(tmp)
        assert idx2.embeddings.shape[0] == len(idx2.chunks) == len(all_chunks)
        print("   OK: persistência mantém chunks e embeddings alinhados")

        print("\n3) busca com pergunta válida...")
        results = idx2.search("requisição get assíncrona", top_k=3)
        assert 1 <= len(results) <= 3
        for r in results:
            assert {"rank", "score", "text", "source_file", "title", "section", "chunk_id"} <= set(r.keys())
        print(f"   OK: {len(results)} resultados, ranks={[r['rank'] for r in results]}")

        print("\n4) casos de borda obrigatórios...")
        for desc, kwargs in [
            ("pergunta vazia", dict(query="", top_k=3)),
            ("top_k=0", dict(query="algo", top_k=0)),
            ("top_k negativo", dict(query="algo", top_k=-3)),
        ]:
            try:
                idx2.search(**kwargs)
                raise AssertionError(f"deveria ter levantado ValueError: {desc}")
            except ValueError as e:
                print(f"   OK {desc} -> {e}")

        results_big = idx2.search("algo", top_k=999999)
        assert len(results_big) == len(all_chunks)
        print(f"   OK top_k maior que o corpus -> clampado para {len(results_big)}")

        empty_idx = FakeRAGIndex()
        try:
            empty_idx.build([])
            raise AssertionError("deveria ter levantado ValueError para corpus vazio")
        except ValueError as e:
            print(f"   OK corpus vazio (build) -> {e}")

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
