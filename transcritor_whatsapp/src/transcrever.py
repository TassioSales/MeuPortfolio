# -*- coding: utf-8 -*-
"""
Transcritor de audios do WhatsApp (100% local, em portugues).

Le todos os audios (.opus/.ogg/.m4a/.mp3/.wav) de uma pasta e gera
transcricoes em .txt e .json usando faster-whisper. Nada e enviado para a
internet alem do download unico do modelo.

Uso:
    python transcrever.py                      # usa ../dados/audios por padrao
    python transcrever.py -p "C:\\pasta"        # outra pasta de audios
    python transcrever.py -m medium            # modelo mais preciso
    python transcrever.py -m large-v3          # so vale a pena com GPU

Retomavel: se parar no meio, rode de novo que ele continua de onde parou.
"""
import os, sys, glob, time, json, argparse

AQUI = os.path.dirname(os.path.abspath(__file__))
PADRAO_AUDIOS = os.path.normpath(os.path.join(AQUI, "..", "dados", "audios"))
PADRAO_SAIDAS = os.path.normpath(os.path.join(AQUI, "..", "dados", "saidas"))
EXTS = ("*.opus", "*.ogg", "*.m4a", "*.mp3", "*.wav")


def detectar_dispositivo(usar_gpu=False):
    """Retorna (device, compute_type).

    Padrao e CPU (int8) por ser o mais compativel. GPU (CUDA) so quando pedido
    com --gpu E as libs CUDA (cuBLAS/cuDNN) realmente carregam; caso contrario
    cai pra CPU com aviso, evitando o erro 'cublas64_12.dll not found'.
    """
    if usar_gpu:
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
            print("Aviso: nenhuma GPU CUDA detectada; usando CPU.")
        except Exception as e:
            print(f"Aviso: GPU indisponivel ({e}); usando CPU.")
    return "cpu", "int8"


def main():
    ap = argparse.ArgumentParser(description="Transcreve audios em portugues (faster-whisper).")
    ap.add_argument("-p", "--pasta", default=PADRAO_AUDIOS, help="Pasta com os audios")
    ap.add_argument("-s", "--saida", default=PADRAO_SAIDAS, help="Pasta de saida")
    ap.add_argument("-m", "--modelo", default="small",
                    help="tiny|base|small|medium|large-v3 (padrao: small)")
    ap.add_argument("-i", "--idioma", default="pt")
    ap.add_argument("--gpu", action="store_true",
                    help="Tenta usar GPU CUDA (requer libs CUDA instaladas)")
    args = ap.parse_args()

    pasta = os.path.abspath(args.pasta)
    saida = os.path.abspath(args.saida)
    os.makedirs(saida, exist_ok=True)

    if not os.path.isdir(pasta):
        sys.exit(f"Pasta de audios nao encontrada: {pasta}")

    files = sorted(f for e in EXTS for f in glob.glob(os.path.join(pasta, e)))
    if not files:
        sys.exit(f"Nenhum audio encontrado em: {pasta}")

    out_txt = os.path.join(saida, "transcricoes.txt")
    out_json = os.path.join(saida, "transcricoes.json")

    # retomar do que ja foi feito
    done = {}
    if os.path.exists(out_json):
        try:
            done = {d["file"]: d for d in json.load(open(out_json, encoding="utf-8"))}
        except Exception:
            done = {}

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper nao instalado. Rode:  pip install -r requirements.txt")

    device, compute = detectar_dispositivo(args.gpu)
    print(f"{len(files)} audios | {len(done)} ja feitos | modelo={args.modelo} | {device}/{compute}")
    model = WhisperModel(args.modelo, device=device, compute_type=compute)

    results = list(done.values())
    t0 = time.time()
    for i, path in enumerate(files, 1):
        name = os.path.basename(path)
        if name in done:
            continue
        try:
            segs, info = model.transcribe(path, language=args.idioma,
                                          vad_filter=True, beam_size=5)
            texto = " ".join(s.text.strip() for s in segs).strip()
            rec = {"file": name, "duration": round(info.duration, 1), "text": texto}
        except Exception as e:
            rec = {"file": name, "duration": 0, "text": f"[ERRO: {e}]"}

        results.append(rec)
        results.sort(key=lambda r: r["file"])
        # salva incremental (nao perde progresso se travar)
        json.dump(results, open(out_json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        with open(out_txt, "w", encoding="utf-8") as f:
            for r in results:
                f.write(f"=== {r['file']}  ({r['duration']}s) ===\n{r['text']}\n\n")

        print(f"[{i}/{len(files)}] {name}: {rec['text'][:70]}")

    print(f"\nConcluido em {time.time()-t0:.0f}s")
    print(f"  Texto: {out_txt}")
    print(f"  JSON:  {out_json}")


if __name__ == "__main__":
    main()
