"""
Gerador de conteúdo por IA (admin only).
Orquestra a pipeline NVIDIA NIM completa:
  1. Roteiro     → mistralai/mistral-medium-3.5-128b
  2. Segurança   → nvidia/nemotron-3-content-safety
  3. Voz (TTS)   → resemble-ai/chatterbox-multilingual-tts
  4. Imagens     → qwen/qwen-image
  5. Vídeo clips → nvidia/cosmos3-nano
  6. Lip-sync    → nvidia/lip-sync
  7. Montagem    → FFmpeg
  8. Validação   → nvidia/synthetic-video-detector
"""
from pathlib import Path
from typing import Dict
from loguru import logger

OUTPUT_DIR = Path("generated_videos")
OUTPUT_DIR.mkdir(exist_ok=True)


async def gerar_conteudo(params: Dict) -> str:
    """
    Ponto de entrada principal — chamado pelo admin route e pelo Celery job.
    Retorna URL (local ou CDN) do vídeo gerado.
    """
    from services.nvidia_ai import pipeline_geracao_episodio

    tema = params.get("tema", "Romance")
    num_ep = params.get("numero_episodio", 1)
    logger.info(f"Iniciando geração: tema={tema}, ep={num_ep}")

    resultado = await pipeline_geracao_episodio(params, output_dir=OUTPUT_DIR)

    video_final = resultado.get("video_final")
    if not video_final:
        raise RuntimeError("Pipeline não produziu vídeo final")

    # Converte path local → URL servível
    if not video_final.startswith("http"):
        video_path = Path(video_final)
        url = f"/generated/{video_path.name}"
    else:
        url = video_final

    if resultado["erros"]:
        logger.warning(f"Pipeline com {len(resultado['erros'])} erro(s): {resultado['erros']}")

    logger.info(f"Geração concluída → {url}")
    return url
