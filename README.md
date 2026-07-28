# Proxy Scraper Bot

Um bot de Telegram que busca proxies públicos de múltiplas fontes de forma automática e eficiente.

## Características

- 🤖 **Bot de Telegram**: Interface simples e intuitiva
- 🌐 **17 fontes de proxies**: Busca em repositórios do GitHub e APIs públicas
- 🔄 **Deduplicação automática**: Remove proxies duplicados
- ⚡ **Busca rápida**: Busca paralela em todas as fontes (~5-10 segundos)
- 📊 **Estatísticas**: Mostra número total de proxies encontrados
- 🔧 **Módulo reutilizável**: Use o `proxy_scraper.py` em outros projetos

## Requisitos

- Python 3.10+
- pip

## Instalação

### 1. Clone ou copie o repositório

```bash
cd ProxyScraper
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o token do Telegram

1. Crie um ficheiro `.env`:
```bash
cp .env.example .env
```

2. Edite `.env` e adicione seu token:
```
TELEGRAM_BOT_TOKEN=seu_token_aqui
```

**Como obter um token:**
- Abra o Telegram e procure por `@BotFather`
- Envie `/newbot` e siga as instruções
- Copie o token gerado

## Uso

### Bot de Telegram

```bash
python telegram_bot.py
```

Comandos disponíveis:
- `/start` - Mostra boas-vindas e instruções
- `/proxies` - Busca e envia proxies
- `/export` - Escolhe tipo e filtra apenas proxies vivos ou todos
- `/help` - Mostra ajuda detalhada

### Módulo Python

Use o scraper em seus próprios projetos:

```python
import asyncio
from proxy_scraper import scrape_proxies

async def main():
    proxies = await scrape_proxies()
    print(f"Encontrados {len(proxies)} proxies")

asyncio.run(main())
```

Com printer customizado:

```python
async def main():
    def my_printer(msg):
        print(f"[LOG] {msg}")
    
    proxies = await scrape_proxies(printer=my_printer)
```

## Fontes de Proxies

- TheSpeedX
- monosans
- proxifly
- ShiftyTR (HTTP e HTTPS)
- roosterkid
- sunny9577
- rdavydov
- Anonym0usWork12
- officialputuid
- mmpx12 (HTTP e HTTPS)
- iplocate (HTTP e HTTPS)
- openproxylist.xyz
- proxyscrape.com
- geonode.com

## Estrutura do Projeto

```
ProxyScraper/
├── proxy_scraper.py        # Módulo de scraping
├── telegram_bot.py         # Bot de Telegram
├── requirements.txt        # Dependências
├── .env.example           # Exemplo de variáveis
├── .github/
│   └── copilot-instructions.md
└── README.md
```

## Notas Importantes

- **Proxies públicos gratuitos**: ~2-5% funcionam em média
- **Limite de requisições**: Alguns sites têm rate limits, mas o bot espera entre requisições
- **Sem garantias**: Use por sua conta e risco
- **Atualizado frequentemente**: Execute `/proxies` novamente para buscar a lista mais recente

## Troubleshooting

### Bot não responde
- Verifique se o `TELEGRAM_BOT_TOKEN` está correto
- Verifique conexão com a internet
- Veja logs do bot

### Nenhum proxy encontrado
- Uma ou mais fontes pode estar offline
- Tente novamente em alguns minutos
- Verifique sua conexão de rede

### Timeout ao buscar proxies
- Seu ISP pode estar bloqueando GitHub
- Use um VPN ou proxy HTTP para contornar
- Tente novamente mais tarde

## Licença

MIT

## Autor

Desenvolvido como projeto de teste e demonstração.
