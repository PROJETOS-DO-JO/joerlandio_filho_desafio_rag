# RAG-HTTPX — núcleo de recuperação sobre a documentação do HTTPX

## Identificação

- Nome do aluno: Joerlândio Filho
- Formato da solução: script de terminal (Python puro, roda no VS Code / qualquer terminal)
- Link do vídeo: _preencher antes da entrega_
- Link do Colab, se aplicável: não se aplica (projeto local)

## Objetivo

Este projeto implementa o **núcleo de recuperação** de um RAG (Retrieval-Augmented
Generation) sobre a documentação oficial do [HTTPX](https://github.com/encode/httpx)
(pasta `docs/`, commit `b5addb64f0161ff6bfe94c124ef76f6a1fba5254`, 23 arquivos `.md`).

Dado uma pergunta em linguagem natural, o sistema encontra e retorna os trechos
mais relevantes da documentação, com a fonte exata de cada um (arquivo, título,
seção). Opcionalmente, também pode enviar esses trechos para a Gemini API e
gerar uma resposta em linguagem natural fundamentada neles (extensão opcional
— a busca central funciona independentemente disso).

## Arquitetura resumida

```text
repositório (git) → 23 arquivos .md em docs/
                   → chunks (~60-90 palavras, com overlap) + metadados
                   → embeddings (sentence-transformers, multilíngue, local)
                   → índice em memória (persistido em disco: embeddings.npz + metadata.json)
                   → pergunta → embedding da pergunta → similaridade cosseno
                   → top_k resultados ordenados, com fonte e score
                   → [opcional] contexto enviado à Gemini API → resposta gerada
```

## Como executar do zero

1. **Python**: 3.10 ou superior (testado com 3.11).
2. **Instalar dependências** (dentro da pasta do projeto):

   ```bash
   pip install -r requirements.txt
   ```

   Isso instala `sentence-transformers` (e o `torch` que ele usa por baixo,
   rodando em CPU — não é necessário GPU nem computador potente),
   `numpy` e `google-generativeai` (só usada se você optar pela geração opcional).

3. **Construir o índice** (clona o repositório HTTPX automaticamente no commit
   fixado pelo desafio, lê os documentos, cria os chunks e calcula os embeddings):

   ```bash
   python build_index.py
   ```

   Na primeira execução, isso baixa o modelo de embeddings (~470 MB, uma vez só,
   fica em cache) e clona o repositório httpx. Leva alguns minutos dependendo da
   internet; execuções seguintes reaproveitam o índice salvo em `index/`.

4. **Fazer uma pergunta**, sem alterar nenhum código:

   ```bash
   python query.py "Como faço uma requisição GET assíncrona com o httpx?"
   python query.py "Como funciona o tratamento de timeouts?" --top-k 5
   python query.py                     # modo interativo (várias perguntas seguidas)
   ```

5. **Extensão opcional — gerar resposta com a Gemini API**:

   ```bash
   # defina a chave (nunca deixe no código; veja .env.example)
   export GEMINI_API_KEY="sua_chave_aqui"      # Linux/Mac
   $env:GEMINI_API_KEY = "sua_chave_aqui"      # Windows PowerShell

   python query.py "Como usar autenticação básica no httpx?" --generate
   ```

   Se a chave não estiver definida, ou a chamada à API falhar, o programa
   **não quebra**: mostra os resultados da busca normalmente e apenas informa
   que a geração está desativada/indisponível.

6. **Rodar as 3 perguntas obrigatórias do desafio** (gera `demo_output.md` como evidência):

   ```bash
   python demo_perguntas.py
   ```

7. **Rodar os testes automatizados** (extensão opcional; valida a mecânica do
   pipeline — chunking, metadados, persistência do índice e tratamento de
   erros — usando um embedding falso e determinístico, para não depender de
   baixar o modelo real só para testar lógica):

   ```bash
   python tests/test_pipeline.py
   ```

## Decisões técnicas

### Chunking

- **Estratégia (duas etapas)**:
  1. Cada arquivo `.md` é primeiro dividido em *seções* pelos cabeçalhos
     Markdown (`#`, `##`, `###`...), ignorando `#` que aparece dentro de
     blocos de código (para não confundir comentários Python com títulos) e
     removendo tags HTML "cruas" que alguns arquivos embutem no Markdown
     (ex.: `<div>`/`<img>`/`<figcaption>` usados para imagens com legenda) —
     preservadas apenas dentro de blocos de código, onde costumam ser saída
     literal do REPL (`<Response [200 OK]>`), não marcação.
  2. Dentro de cada seção, o texto é dividido em **blocos "atômicos"**: um
     bloco de código (` ``` `) inteiro nunca é cortado no meio; cada item de
     uma lista Markdown (`* item`, `- item`, `1. item`) também vira seu
     próprio bloco (evitando que vários itens de lista fiquem colados numa
     única frase corrida); e um parágrafo de texto comum (entre linhas em
     branco) é outro tipo de bloco. Esses blocos são então agrupados em
     chunks de ~75 palavras, unidos com quebra de linha dupla — preservando
     a formatação original (títulos, parágrafos, listas e código continuam
     visualmente separados), em vez de "achatar" tudo numa única linha
     corrida.
  3. Marcações de negrito/itálico do Markdown (`**palavra**`, `*palavra*`) são
     removidas do texto exibido — mesmo quando atravessam mais de uma linha —
     porque só poluem a leitura de um trecho mostrado como texto puro no
     terminal. Marcadores de lista (`*`/`+`) são normalizados para `-`. Nada
     disso toca o conteúdo de blocos de código ou trechos entre crases
     (` `código` `), onde um `*`/`**` costuma ser parte real do código
     (ex.: `2 * 3`, `**kwargs`).
- **Tamanho aproximado**: alvo de 75 palavras por chunk (dentro da faixa
  recomendada de 60-90); um teto de segurança (150 palavras) evita que um
  bloco de código isolado muito longo vire um chunk gigantesco — nesse caso
  raro, ele é dividido por contagem de palavras.
- **Overlap**: o último bloco de um chunk é repetido como primeiro bloco do
  chunk seguinte da mesma seção, para não perder contexto nas bordas.
- **Justificativa**: seções pequenas (ex.: um item de lista com poucas linhas)
  viram um único chunk pequeno — isso é aceitável e preserva o contexto
  completo daquele trecho. Seções grandes (ex.: "Quickstart") são divididas em
  vários chunks com sobreposição. A primeira versão do chunking dividia o
  texto só por contagem de palavras (sem respeitar blocos de código/parágrafos),
  o que produzia chunks tecnicamente corretos mas visualmente "poluídos"
  (título, texto e código todos numa linha só). Trocar para blocos atômicos
  resolveu isso sem perder precisão.

### Embeddings e busca

- **Modelo**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  — público, gratuito, sem API key, multilíngue (importante porque as
  perguntas de teste são em português e a documentação está em inglês).
- **Forma de cálculo da similaridade**: os embeddings são normalizados
  (`normalize_embeddings=True`), então o produto escalar entre dois vetores
  já é equivalente à similaridade cosseno — usamos uma simples multiplicação
  de matrizes em memória (`numpy`), sem necessidade de banco vetorial dado o
  tamanho do corpus (algumas centenas de chunks).
- **`top_k`**: padrão 3, configurável via `--top-k` (o desafio pede entre 3 e 5).
- **Justificativa**: para um corpus deste tamanho (dezenas de arquivos,
  algumas centenas de chunks), uma matriz densa em memória é simples,
  rápida o bastante e evita a complexidade de configurar um banco vetorial
  específico — que, segundo o próprio enunciado, não vale pontos extras.

### Persistência do índice (extensão opcional)

Depois de calculado uma vez, o índice (embeddings + metadados) é salvo em
`index/embeddings.npz` + `index/metadata.json`. Consultas seguintes (`query.py`,
`demo_perguntas.py`) carregam esse índice já pronto, sem recalcular os
embeddings — só é necessário rodar `build_index.py` de novo se a documentação
mudar.

### Metadados e fontes

Cada chunk carrega, desde a criação até a exibição do resultado:

```text
texto | source_file (ex.: docs/quickstart.md) | title (título do documento) |
section (cabeçalho mais próximo) | chunk_id (identificador único e rastreável)
```

Os índices da lista de chunks e da matriz de embeddings permanecem sempre
alinhados (o chunk na posição `i` corresponde exatamente ao embedding na
linha `i`), tanto em memória quanto ao salvar/carregar do disco — por isso a
fonte exibida em cada resultado sempre corresponde ao texto exibido.

## Perguntas de teste

Executadas em `demo_perguntas.py` (evidência salva em `demo_output.md` após rodar
o script — **rode `python demo_perguntas.py` na sua máquina e cole/anexe o
`demo_output.md` gerado, ou os prints do terminal, como evidência final**).

### 1. Pergunta com resposta clara

- Pergunta: "Como faço uma requisição GET assíncrona com o httpx?"
- Resultado esperado: um chunk vindo de `docs/quickstart.md` ou `docs/async.md`
  mencionando `httpx.AsyncClient` / `await client.get(...)`.
- O resultado foi relevante?

 RESPOSTA:
  Parcialmente. Com top_k=3, os resultados vieram de advanced/proxies.md, quickstart.md e third_party_packages.md — relacionados a fazer requisições HTTP, mas nenhum focado especificamente em código assíncrono. Aumentando para top_k=5, o chunk de async.md (o mais direto sobre a pergunta) apareceu, mas só na 4ª posição. Isso mostra que top_k=3 pode não ser suficiente para perguntas cuja resposta mais específica não é o trecho "mais parecido" textualmente.

### 2. Pergunta ampla ou ambígua

- Pergunta: "Como o httpx lida com timeouts e configurações de conexão?"
- Resultado esperado: trechos de `docs/advanced/timeouts.md` e possivelmente
  `docs/advanced/clients.md` ou `docs/quickstart.md`.
- O resultado foi relevante? 

  RESPOSTA:
  Muito relevante — os 3 primeiros resultados vieram de advanced/timeouts.md
  (seções "Fine tuning the configuration" e "Timeouts") e quickstart.md
  (seção "Timeouts"), com scores altos e próximos entre si (0.75, 0.72, 0.70),
  mostrando que o sistema encontrou consistentemente o conteúdo certo sobre
  timeouts (ver `demo_output.md` para os valores exatos da última execução).

### 3. Pergunta fora do escopo

- Pergunta: "Qual é a receita de um bolo de chocolate?"
- Como o sistema reagiu: continua retornando os `top_k` chunks mais próximos
  (a busca por similaridade sempre devolve algo, mesmo que a similaridade seja
  baixa) — não existe um mecanismo de "recusa" automática.
- Como essa reação poderia melhorar: poderia ser adicionado um limiar mínimo de
  score; abaixo dele, o sistema informaria explicitamente que não encontrou
  nada relevante na documentação, em vez de devolver o "menos ruim" dos chunks.

## Extra: interface web local

Além da CLI (`query.py`), o projeto inclui uma interface web local opcional
(`app.py` + `templates/index.html` + `src/render.py`), feita **depois** de
todo o núcleo obrigatório estar pronto — não vale pontos na correção, é só
uma forma mais visual de testar perguntas. Ela chama exatamente a mesma
lógica de busca (`RAGIndex.search()`), sem duplicar nada.

```bash
python app.py
# depois abra http://127.0.0.1:5000 no navegador
```

## Casos de borda tratados

- **Pergunta vazia**: `search()` levanta um erro com mensagem clara em vez de
  travar ou retornar um resultado sem sentido.
- **Corpus sem documentos**: `build_index.py` interrompe com uma mensagem
  explicando o problema se nenhum `.md` for encontrado; `RAGIndex.search()`
  também recusa rodar sobre um índice vazio.
- **`top_k` inválido**: valores `<= 0` ou não inteiros geram uma mensagem
  compreensível; valores maiores que o número de chunks disponíveis são
  automaticamente reduzidos ("clampados") ao total existente.

Veja `tests/test_pipeline.py` para os testes automatizados desses casos.

## Limitações conhecidas

- Algumas seções muito curtas (ex.: um cabeçalho seguido imediatamente por um
  subcabeçalho, como em `docs/third_party_packages.md`) geram chunks pequenos
  (só o título, sem corpo). Isso é esperado dado o formato do documento, mas
  reduz um pouco a utilidade desses chunks específicos como resultado de busca.
- A busca por similaridade nunca "recusa" responder: mesmo para uma pergunta
  totalmente fora do escopo (item 3 acima), sempre devolve os `top_k` chunks
  mais próximos disponíveis — a diferenciação fica por conta do score, que fica
  visivelmente mais baixo nesses casos.
- Blocos de código são preservados inteiros dentro de um chunk (nunca cortados
  no meio), a menos que um único bloco isolado ultrapasse 150 palavras — caso
  raro na documentação do httpx, tratado com um fallback por contagem de
  palavras.
- A pergunta é comparada contra o embedding de cada chunk individualmente; um
  trecho de código sozinho (pouco texto ao redor) carrega menos "significado"
  linguístico para o modelo comparar do que um parágrafo explicativo — por
  isso, perguntas cuja resposta está majoritariamente em código (ex.: um
  exemplo específico de sintaxe) podem receber score mais baixo do que
  perguntas respondidas por texto explicativo, mesmo quando o trecho de
  código é tecnicamente a resposta certa (ver reflexão da Pergunta 1 acima).
- A extensão de geração depende da disponibilidade do nível gratuito da Gemini
  API no momento do uso; durante o desenvolvimento, o modelo usado inicialmente
  (`gemini-2.5-flash`) já havia sido descontinuado para novas contas, e foi
  trocado para `gemini-3.6-flash`. Se o modelo padrão configurado parar de
  funcionar no futuro, defina a variável de ambiente `GEMINI_MODEL` com um
  modelo atual (veja `.env.example`).
- A biblioteca `google-generativeai` usada na geração opcional está marcada
  como descontinuada pelo Google (emite um aviso `FutureWarning`, mas
  continua funcionando normalmente); a sucessora é a biblioteca `google-genai`.

## Uso de ferramentas de IA

- Ferramentas utilizadas: Claude (Anthropic), via Claude em modo Cowork.
- Tarefas em que ajudaram: leitura e interpretação do enunciado do desafio;
  desenho da arquitetura do pipeline (chunking → embeddings → busca);
  implementação do código (chunking, indexação, busca, CLI, geração opcional);
  escrita dos testes automatizados; escrita deste README.
- Exemplo representativo de prompt ou orientação: "Construa o núcleo de
  recuperação de um RAG usando a documentação do HTTPX, seguindo os requisitos
  obrigatórios do desafio (chunking com metadados, embeddings, busca por
  similaridade, tratamento de erros, 3 perguntas de teste)."
- O que foi testado, modificado ou validado por você: instalei as dependências
  (pip install -r requirements.txt), configurei o Git no meu PC, rodei
  build_index.py e confirmei os 23 arquivos e 359 chunks gerados. Testei as 3
  perguntas obrigatórias manualmente (python query.py) e comparei os resultados
  com top_k=3 e top_k=5, conferindo se os trechos e as fontes faziam sentido.
  Testei também os casos de borda (pergunta vazia, top_k inválido). Rodei
  demo_perguntas.py para gerar a evidência final (demo_output.md). Li o
  README completo e entendo a arquitetura e as decisões técnicas para poder
  explicar no vídeo.

> Durante o desenvolvimento assistido, foi encontrado e corrigido um bug real:
> a detecção de cabeçalhos Markdown inicialmente também capturava comentários
> `# ...` dentro de blocos de código Python (ex.: em `docs/advanced/extensions.md`),
> fragmentando o documento em seções sem sentido. A correção passou a ignorar
> linhas dentro de blocos ` ``` ` ao procurar por cabeçalhos.

## Referências e código externo

- Documentação oficial do HTTPX: <https://github.com/encode/httpx>
- Guia de busca semântica do Sentence Transformers: <https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html>
- Modelo de embeddings: <https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2>
- Início rápido da Gemini API: <https://ai.google.dev/gemini-api/docs/get-started>
- Preços/modelos gratuitos da Gemini API: <https://ai.google.dev/gemini-api/docs/pricing>

## Segurança

- [x] Minha solução usa segredo protegido (`GEMINI_API_KEY` via variável de
      ambiente, nunca escrita no código) e nenhuma chave foi publicada.
      (O núcleo obrigatório de busca não usa nenhuma API key.)

## Estrutura do projeto

```text
.
├── README.md                 este arquivo
├── requirements.txt          dependências Python
├── .env.example               modelo de variáveis de ambiente (chave da Gemini)
├── build_index.py            clona o repo, gera chunks e embeddings, salva o índice
├── query.py                  consulta o índice (CLI / modo interativo)
├── demo_perguntas.py         roda as 3 perguntas obrigatórias e salva evidência
├── app.py                     extra (fora do escopo obrigatório): interface web local
├── templates/
│   └── index.html            extra: página da interface web (usa a mesma busca de query.py)
├── src/
│   ├── fetch_docs.py         clone/checkout do repositório + busca de .md
│   ├── chunking.py           parsing de Markdown + divisão em chunks com metadados
│   ├── indexer.py            embeddings, índice em memória, busca, persistência
│   ├── generate.py           extensão opcional: geração de resposta via Gemini
│   └── render.py              extra: converte o texto do chunk em HTML pra interface web
├── tests/
│   └── test_pipeline.py      testes automatizados (extensão opcional)
├── httpx_repo/                (gerado ao rodar build_index.py; não versionar)
└── index/                     (gerado ao rodar build_index.py; não versionar)
```
