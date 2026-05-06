import os
from pathlib import Path

import httpx


MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"


def generate_ai_response(message: str, portfolio_data: list, risk_metrics: dict):
    api_key = _get_mistral_key()
    if api_key:
        try:
            return _generate_mistral_response(api_key, message, portfolio_data, risk_metrics)
        except Exception as exc:
            print(f"Mistral fallback activated: {exc}")

    return generate_local_response(message, portfolio_data, risk_metrics)


def generate_local_response(message: str, portfolio_data: list, risk_metrics: dict):
    msg = message.lower()
    
    total_val = sum([p['current_value'] for p in portfolio_data])
    ativos = [p['asset']['ticker'] for p in portfolio_data]
    
    if "risco" in msg or "seguro" in msg:
        vol = risk_metrics.get("portfolio_volatility", 0) * 100
        if vol > 25:
            return f"**Alerta de Risco Alto!** Sua volatilidade anualizada está em {vol:.1f}%. Eu recomendo diversificar para ativos mais seguros (como Renda Fixa ou ETFs como IVVB11) se você não tiver estômago para grandes quedas."
        else:
            return f"Sua carteira está com um perfil moderado/conservador. Volatilidade em {vol:.1f}%. Está bem balanceada."
            
    if "otimiza" in msg or "markowitz" in msg or "ideal" in msg or "melhorar" in msg:
        weights = risk_metrics.get("optimal_weights", {})
        if not weights:
            return "Adicione mais ativos na sua carteira para eu rodar o algoritmo de Markowitz."
        response = "Rodando o modelo da Fronteira Eficiente (Markowitz), a alocação matemática ideal para maximizar seus lucros e reduzir o risco seria:\n\n"
        for t, w in weights.items():
            if w > 0.01:
                response += f"- **{t}**: {w*100:.1f}%\n"
        return response

    if "carteira" in msg or "resumo" in msg:
        return f"Você tem R$ {total_val:.2f} investidos em {len(ativos)} ativos ({', '.join(ativos[:3])}...). Seu Índice de Sharpe é {risk_metrics.get('portfolio_sharpe', 0):.2f}. Se o Sharpe estiver abaixo de 0.5, você está assumindo risco demais para pouco lucro."

    return ("Olá! Eu sou o WealthMap AI, seu analista quantitativo. "
            "Posso analisar o **Risco**, **Otimizar** sua carteira via Markowitz, ou fazer um **Resumo** "
            "financeiro. O que você deseja?")


def _generate_mistral_response(api_key: str, message: str, portfolio_data: list, risk_metrics: dict):
    model = os.getenv("MISTRAL_MODEL", DEFAULT_MODEL)
    portfolio_context = _build_portfolio_context(portfolio_data, risk_metrics)
    payload = {
        "model": model,
        "temperature": 0.25,
        "max_tokens": 900,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Voce e o WealthMap AI, um analista financeiro senior para um dashboard de carteira. "
                    "Responda em portugues do Brasil, com tom profissional e direto. "
                    "Use somente os dados fornecidos como contexto. "
                    "Sempre destaque riscos, concentracao, diversificacao e proximas acoes praticas. "
                    "Nao prometa rentabilidade e nao diga que esta dando consultoria financeira personalizada. "
                    "Use markdown curto, com no maximo 5 bullets quando fizer sentido."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Contexto atual da carteira:\n"
                    f"{portfolio_context}\n\n"
                    f"Pergunta do usuario: {message}"
                ),
            },
        ],
    }

    with httpx.Client(timeout=35) as client:
        response = client.post(
            MISTRAL_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        decoded = response.json()

    choices = decoded.get("choices", [])
    if not choices:
        raise RuntimeError("resposta vazia da Mistral")

    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("conteudo vazio da Mistral")
    return content


def _build_portfolio_context(portfolio_data: list, risk_metrics: dict):
    total_value = sum(float(p.get("current_value", 0)) for p in portfolio_data)
    total_invested = sum(float(p.get("total_invested", 0)) for p in portfolio_data)
    total_profit = total_value - total_invested
    total_return = (total_profit / total_invested * 100) if total_invested else 0

    lines = [
        f"Valor total: R$ {total_value:,.2f}",
        f"Capital investido: R$ {total_invested:,.2f}",
        f"Resultado: R$ {total_profit:,.2f} ({total_return:.2f}%)",
        f"Sharpe da carteira: {float(risk_metrics.get('portfolio_sharpe', 0)):.2f}",
        f"Volatilidade anual: {float(risk_metrics.get('portfolio_volatility', 0)) * 100:.2f}%",
        "Posicoes:",
    ]

    for position in sorted(portfolio_data, key=lambda item: item.get("current_value", 0), reverse=True)[:12]:
        asset = position.get("asset", {})
        value = float(position.get("current_value", 0))
        weight = (value / total_value * 100) if total_value else 0
        lines.append(
            "- "
            f"{asset.get('ticker', 'N/A')} ({asset.get('asset_type', 'N/A')}): "
            f"peso {weight:.1f}%, valor R$ {value:,.2f}, "
            f"P/L {float(position.get('profit_loss_percentage', 0)):.2f}%"
        )

    optimal_weights = risk_metrics.get("optimal_weights") or {}
    if optimal_weights:
        lines.append("Pesos sugeridos pelo modelo quantitativo:")
        for ticker, weight in optimal_weights.items():
            lines.append(f"- {ticker}: {float(weight) * 100:.1f}%")

    return "\n".join(lines)


def _get_mistral_key():
    _load_env_candidates()
    return os.getenv("MISTRAL_API_KEY", "").strip()


def get_ai_status():
    has_key = bool(_get_mistral_key())
    return {
        "provider": "mistral" if has_key else "local",
        "model": os.getenv("MISTRAL_MODEL", DEFAULT_MODEL) if has_key else "local-rules",
    }


def _load_env_candidates():
    candidates = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path.cwd().parent.parent / "documind_local" / ".env",
    ]

    for path in candidates:
        if path.exists():
            _load_env_file(path)


def _load_env_file(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
