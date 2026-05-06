# DocuMind Local

Gerenciador local de documentos com upload, extracao de texto, busca e analise com Mistral.

## Rodar

```bat
start_documind.bat
```

## Fluxo de estudo

- `Dashboard`: fila de revisões do dia e materiais recentes.
- `Biblioteca`: todos os materiais importados, filtro de PDFs e botão de excluir.
- `Upload`: importa PDF/TXT/DOCX/XLSX e cria plano de estudos.
- `Revisão`: mostra objetivos, agenda espaçada, tópicos e flashcards.
- `Pesquisa`: gera buscas úteis para temas, apostilas e PDFs online.

Abra:

```txt
http://localhost:8093
```

## O que a V1 faz

- Upload de arquivos.
- Extracao de texto de `.txt`, `.md`, `.csv`, `.json`, `.html`, `.pdf`, `.docx` e `.xlsx`.
- Analise com Mistral: resumo, tags, entidades, tipo do documento, acoes sugeridas e nivel de risco.
- Busca local por titulo, nome de arquivo, texto, tags e entidades.
- Banco local em JSON.

## PDF com Python

Para PDFs, o projeto usa um extrator Python com varias bibliotecas em cascata:

- PyMuPDF
- pdfplumber
- pypdf
- OCR opcional com pdf2image + pytesseract

Instale com:

```bat
install_pdf_tools.bat
```

Para reprocessar documentos ja enviados:

```bat
reprocess_documind.bat
```

## API

- `GET /api/health`
- `GET /api/documents`
- `GET /api/documents/{id}`
- `POST /api/documents`
- `POST /api/documents/{id}/analyze`
- `GET /api/search?q=termo`

## Configuracao

As variaveis ficam em `.env`.

```txt
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest
ADDR=:8093
```
