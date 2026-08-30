# Evidências de execução — 2026-08-28 23:31

## 1. Pergunta com resposta clara na documentação

**Pergunta:** Como faço uma requisição GET assíncrona com o httpx?

**[1]** score=0.5892 | fonte=`docs/advanced/proxies.md` | título/seção: Proxies / Proxies

> HTTPX supports setting up [HTTP proxies](https://en.wikipedia.org/wiki/Proxy_server#Web_proxy_servers) via the `proxy` parameter to be passed on client initialization or top-level API functions like `httpx.get(..., proxy=...)`.

Diagram of how a proxy works (source: Wikipedia). The left hand side "Internet" blob may be your HTTPX client requesting example.com through a proxy.

**[2]** score=0.5766 | fonte=`docs/quickstart.md` | título/seção: QuickStart / QuickStart

> # QuickStart

First, start by importing HTTPX:

```pycon
>>> import httpx
```

Now, let’s try to get a webpage.

```pycon
>>> r = httpx.get('https://httpbin.org/get')
>>> r
<Response [200 OK]>
```

Similarly, to make an HTTP POST request:

```pycon
>>> r = httpx.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

**[3]** score=0.5673 | fonte=`docs/third_party_packages.md` | título/seção: Third Party Packages / httpx-sse

> ### httpx-sse

[GitHub](https://github.com/florimondmanca/httpx-sse)

Allows consuming Server-Sent Events (SSE) with HTTPX.


**Resposta em português (gerada via Gemini):**

Não encontrei essa informação na documentação fornecida. O contexto disponibilizado (dos arquivos `docs/quickstart.md`, `docs/advanced/proxies.md` e `docs/third_party_packages.md`) mostra apenas como realizar requisições GET de forma síncrona, não contendo instruções sobre como fazer requisições assíncronas.

---

## 2. Pergunta ampla ou ambígua

**Pergunta:** Como o httpx lida com timeouts e configurações de conexão?

**[1]** score=0.7461 | fonte=`docs/advanced/timeouts.md` | título/seção: Timeouts / Fine tuning the configuration

> ## Fine tuning the configuration

HTTPX also allows you to specify the timeout behavior in more fine grained detail.

There are four different types of timeouts that may occur. These are connect,
read, write, and pool timeouts.

- The connect timeout specifies the maximum amount of time to wait until
a socket connection to the requested host is established. If HTTPX is unable to connect
within this time frame, a `ConnectTimeout` exception is raised.

**[2]** score=0.7198 | fonte=`docs/quickstart.md` | título/seção: QuickStart / Timeouts

> ## Timeouts

HTTPX defaults to including reasonable timeouts for all network operations,
meaning that if a connection is not properly established then it should always
raise an error rather than hanging indefinitely.

The default timeout for network inactivity is five seconds. You can modify the
value to be more or less strict:

```pycon
>>> httpx.get('https://github.com/', timeout=0.001)
```

You can also disable the timeout behavior completely...

```pycon
>>> httpx.get('https://github.com/', timeout=None)
```

**[3]** score=0.6963 | fonte=`docs/advanced/timeouts.md` | título/seção: Timeouts / Timeouts

> HTTPX is careful to enforce timeouts everywhere by default.

The default behavior is to raise a `TimeoutException` after 5 seconds of
network inactivity.


**Resposta em português (gerada via Gemini):**

Com base na documentação fornecida, o HTTPX lida com timeouts e configurações de conexão da seguinte forma:

* **Comportamento Padrão:** O HTTPX inclui timeouts por padrão para todas as operações de rede para evitar que as requisições fiquem travadas indefinidamente. O timeout padrão para inatividade de rede é de 5 segundos, após o qual é lançada uma exceção `TimeoutException` (`docs/quickstart.md`, `docs/advanced/timeouts.md`).
* **Personalização e Desativação:** É possível alterar o valor do timeout para torná-lo mais ou menos rigoroso (ex: `timeout=0.001`) ou desativar o comportamento de timeout completamente usando `timeout=None` (`docs/quickstart.md`).
* **Ajuste Fino da Configuração:** O HTTPX permite especificar o comportamento de timeout em detalhes mais específicos, dividindo-os em quatro tipos (`docs/advanced/timeouts.md`):
  1. **Connect:** Especifica o tempo máximo de espera até que uma conexão de socket com o host solicitado seja estabelecida. Caso não consiga conectar nesse período, lança uma exceção `ConnectTimeout` (`docs/advanced/timeouts.md`).
  2. **Read** (`docs/advanced/timeouts.md`).
  3. **Write** (`docs/advanced/timeouts.md`).
  4. **Pool** (`docs/advanced/timeouts.md`).

---

## 3. Pergunta fora do escopo da base

**Pergunta:** Qual é a receita de um bolo de chocolate?

**[1]** score=0.3376 | fonte=`docs/quickstart.md` | título/seção: QuickStart / Cookies

> ## Cookies

Any cookies that are set on the response can be easily accessed:

```pycon
>>> r = httpx.get('https://httpbin.org/cookies/set?chocolate=chip')
>>> r.cookies['chocolate']
'chip'
```

To include cookies in an outgoing request, use the `cookies` parameter:

```pycon
>>> cookies = {"peanut": "butter"}
>>> r = httpx.get('https://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'peanut': 'butter'}}
```

Cookies are returned in a `Cookies` instance, which is a dict-like data structure
with additional API for accessing cookies by their domain or path.

**[2]** score=0.2204 | fonte=`docs/contributing.md` | título/seção: Contributing / Development

> ## Development

To start developing HTTPX create a fork of the
[HTTPX repository](https://github.com/encode/httpx) on GitHub.

Then clone your fork with the following command replacing `YOUR-USERNAME` with
your GitHub username:

```shell
$ git clone https://github.com/YOUR-USERNAME/httpx
```

You can now install the project and its dependencies using:

```shell
$ cd httpx
$ scripts/install
```

**[3]** score=0.2203 | fonte=`docs/quickstart.md` | título/seção: QuickStart / Cookies

> Cookies are returned in a `Cookies` instance, which is a dict-like data structure
with additional API for accessing cookies by their domain or path.

```pycon
>>> cookies = httpx.Cookies()
>>> cookies.set('cookie_on_domain', 'hello, there!', domain='httpbin.org')
>>> cookies.set('cookie_off_domain', 'nope.', domain='example.org')
>>> r = httpx.get('http://httpbin.org/cookies', cookies=cookies)
>>> r.json()
{'cookies': {'cookie_on_domain': 'hello, there!'}}
```


**Resposta em português (gerada via Gemini):**

Não encontrei essa informação na documentação fornecida.

---

## Casos de borda (tratamento de erros)

- **Pergunta vazia:** mensagem tratada -> "A pergunta está vazia. Digite uma pergunta antes de buscar."
- **top_k inválido (0):** mensagem tratada -> "top_k inválido: 0. Use um número inteiro positivo (ex.: 3, 4 ou 5)."
- **top_k inválido (-1):** mensagem tratada -> "top_k inválido: -1. Use um número inteiro positivo (ex.: 3, 4 ou 5)."
- **top_k não-inteiro (2.5):** mensagem tratada -> "top_k inválido: 2.5. Use um número inteiro positivo (ex.: 3, 4 ou 5)."