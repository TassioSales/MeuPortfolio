# News Sentiment Radar

Dashboard de analise de sentimento de noticias via RSS.

## O que faz

- Coleta manchetes e resumos de fontes RSS publicas.
- Classifica sentimento: positivo, neutro ou negativo.
- Classifica setor: economia, politica, tecnologia, saude ou geral.
- Extrai entidades simples de titulos e descricoes.
- Mostra um dashboard com termometro por setor, entidades e noticias recentes.

## Rodar

```bat
start_news_radar.bat
```

Abra:

```txt
http://localhost:8092
```

Para parar:

```bat
stop_news_radar.bat
```

## API

- `GET /api/health`
- `GET /api/sources`
- `GET /api/articles`
- `GET /api/summary`
- `POST /api/refresh`

## Observacao

Se uma fonte RSS estiver fora do ar ou bloquear a coleta, o backend segue funcionando com dados de demonstracao para manter o dashboard navegavel.
