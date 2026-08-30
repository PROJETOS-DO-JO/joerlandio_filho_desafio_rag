"""
Executa as perguntas obrigatórias exigidas pelo desafio e salva as evidências
em demo_output.md:

    1) Uma pergunta cuja resposta está claramente na documentação.
    2) Uma pergunta mais ampla ou ambígua.
    3) Uma pergunta fora do assunto da base (fora do escopo do HTTPX).

Também demonstra o tratamento dos casos de borda obrigatórios: pergunta
vazia e top_k inválido.

Para cada uma das 3 perguntas, também gera (extensão opcional) uma resposta
em português via Gemini, citando as fontes recuperadas. Se a chave da API
não estiver configurada, ou a geração falhar por qualquer motivo, isso não
interrompe a demo — aparece apenas um aviso no lugar da resposta.

Uso:
    python demo_perguntas.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.indexer import RAGIndex
from src.generate import generate_answer

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"
OUTPUT_FILE = BASE_DIR / "demo_output.md"

PERGUNTAS = [
    (
        "1. Pergunta com resposta clara na documentação",
        "Como faço uma requisição GET assíncrona com o httpx?",
    ),
    (
        "2. Pergunta ampla ou ambígua",
        "Como o httpx lida com timeouts e configurações de conexão?",
    ),
    (
        "3. Pergunta fora do escopo da base",
        "Qual é a receita de um bolo de chocolate?",
    ),
]


def format_results_md(results):
    if not results:
        return "_Nenhum resultado retornado._"
    blocks = []
    for r in results:
        blocks.append(
            f"**[{r['rank']}]** score={r['score']:.4f} | fonte=`{r['source_file']}` | "
            f"título/seção: {r['title']} / {r['section']}\n\n> {r['text']}"
        )
    return "\n\n".join(blocks)


def main():
    try:
        index = RAGIndex.load(INDEX_DIR)
    except FileNotFoundError as e:
        raise SystemExit(f"{e}\nRode primeiro: python build_index.py")

    out = [f"# Evidências de execução — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

    for titulo, pergunta in PERGUNTAS:
        out.append(f"## {titulo}\n\n**Pergunta:** {pergunta}\n")
        try:
            results = index.search(pergunta, top_k=3)
            out.append(format_results_md(results))

            print(f"\nGerando resposta em português para: {pergunta}")
            answer = generate_answer(pergunta, results)
            is_fallback = answer.strip().startswith("[Geração")
            label = (
                "Aviso da geração (extensão opcional)"
                if is_fallback
                else "Resposta em português (gerada via Gemini)"
            )
            out.append(f"\n\n**{label}:**\n\n{answer}")
        except ValueError as e:
            out.append(f"_Erro tratado:_ {e}")
        out.append("\n---\n")

    out.append("## Casos de borda (tratamento de erros)\n")
    casos = [
        ("Pergunta vazia", dict(query="", top_k=3)),
        ("top_k inválido (0)", dict(query="O que é o httpx?", top_k=0)),
        ("top_k inválido (-1)", dict(query="O que é o httpx?", top_k=-1)),
        ("top_k não-inteiro (2.5)", dict(query="O que é o httpx?", top_k=2.5)),
    ]
    for desc, kwargs in casos:
        try:
            index.search(**kwargs)
            out.append(f"- **{desc}:** não levantou erro (inesperado).")
        except ValueError as e:
            out.append(f"- **{desc}:** mensagem tratada -> \"{e}\"")

    text = "\n".join(out)
    OUTPUT_FILE.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nEvidências salvas em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
