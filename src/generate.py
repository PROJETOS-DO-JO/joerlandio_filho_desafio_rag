"""
Extensão opcional (Caminho C do desafio): gera uma resposta em linguagem
natural a partir dos melhores trechos recuperados, usando a Gemini API.

Importante: a busca (recuperação) é o núcleo obrigatório do RAG e já funciona
sem esta etapa. Por isso, todo erro aqui é tratado e devolvido como uma
string explicativa, nunca interrompe o programa nem quebra a busca.

Configuração (nunca coloque a chave no código):
    - Defina a variável de ambiente GEMINI_API_KEY antes de rodar com --generate.
    - Use um projeto identificado como "Free" no Google AI Studio.

Exemplos:
    Windows (PowerShell):  $env:GEMINI_API_KEY = "sua_chave_aqui"
    Windows (cmd):         set GEMINI_API_KEY=sua_chave_aqui
    Linux/Mac:             export GEMINI_API_KEY="sua_chave_aqui"
"""
import os

# Modelo padrão: leve e coberto pelo nível gratuito da Gemini Developer API.
# A disponibilidade de modelos muda com o tempo (o "gemini-2.5-flash" usado
# originalmente já foi descontinuado para novas contas) — confira o modelo
# atual em https://ai.google.dev/gemini-api/docs/pricing e, se necessário,
# troque definindo a variável de ambiente GEMINI_MODEL.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def _build_prompt(question, results):
    context_blocks = [
        f"Fonte: {r['source_file']} (seção: {r['section']})\nTrecho: {r['text']}"
        for r in results
    ]
    context = "\n\n".join(context_blocks)
    return f"""Você é um assistente que responde SOMENTE com base no contexto abaixo,
retirado da documentação oficial do HTTPX. Se o contexto não contiver a resposta,
diga claramente que não encontrou essa informação na documentação, em vez de inventar.
Sempre cite os arquivos de origem usados na resposta, entre parênteses.

Contexto:
{context}

Pergunta: {question}

Resposta (em português):"""


def generate_answer(question, results) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "[Geração desativada] Nenhuma variável de ambiente GEMINI_API_KEY foi "
            "encontrada. A busca acima já é o resultado principal exigido pelo desafio; "
            "defina GEMINI_API_KEY para habilitar esta extensão opcional."
        )

    try:
        import google.generativeai as genai
    except ImportError:
        return (
            "[Geração desativada] A biblioteca google-generativeai não está instalada. "
            "Rode: pip install google-generativeai"
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = _build_prompt(question, results)
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        return text.strip() if text else "[Geração falhou] A API não retornou texto."
    except Exception as e:  # nunca deixa a geração derrubar o programa
        return (
            f"[Geração falhou] Não foi possível obter resposta da Gemini API: {e}\n"
            "A busca (recuperação) acima continua válida; a geração é apenas uma extensão opcional."
        )
