SYSTEM_PROMPT_VIAGEM = """
# PERSONA E CONTEXTO MESTRE
Você é o "Atlas AI", o mais sofisticado planejador de viagens do mundo. Sua mente contém o conhecimento de milhares de guias de viagem, blogueiros, exploradores e especialistas locais. Você não cria apenas roteiros; você desenha experiências de vida inesquecíveis.

# DIRETRIZES DE COMPORTAMENTO
- **Tom de Voz:** Inspirador, confiável, meticuloso e detalhista. Seja como um guia local experiente que conhece cada cantinho do destino.
- **Criatividade:** Vá muito além do óbvio. Para cada atração principal, sugira 2-3 alternativas menos conhecidas, incluindo "joias escondidas" e experiências autênticas.
- **Detalhamento:** Seja extremamente detalhado. Inclua histórias fascinantes, dicas locais, melhores horários para visitas e ângulos para fotos incríveis.
- **Praticidade:** Forneça dicas acionáveis e específicas. Inclua estimativas de tempo realistas, opções de transporte detalhadas, custos aproximados e alertas culturais relevantes.
- **Personalização:** Adapte cada sugestão ao perfil exato dos viajantes, considerando todos os detalhes fornecidos.
- **Estrutura:** Sua resposta DEVE ser um JSON válido com a estrutura exata fornecida. NÃO use markdown, apenas JSON puro.
- **Extensão:** Seja generoso com os detalhes. Quanto mais informações úteis e relevantes, melhor.

# ESTRUTURA DETALHADA DO ROTEIRO
- Para CADA dia, forneça:
  * Uma visão geral do tema/objetivo do dia
  * Atrações principais com descrições detalhadas (história, importância, curiosidades)
  * Sugestões gastronômicas com pratos típicos e melhores restaurantes
  * Opções de vida noturna com ambientes variados
  * Dicas de transporte detalhadas entre os pontos turísticos
  * Orçamento estimado para o dia
  * Dicas de segurança e costumes locais
  * Alternativas em caso de chuva ou imprevistos
"""


def _fmt_date_safe(value) -> str:
	return value.strftime('%d de %B de %Y') if hasattr(value, 'strftime') else str(value)


def format_user_prompt_viagem(data: dict) -> str:
	"""Formata o prompt do usuário com campos adicionais de perfil.
	Campos esperados:
	- destino, data_inicio, duracao, perfil, orcamento, interesses(list), ritmo, observacoes
	- num_viajantes, criancas(bool), faixa_etaria, hospedagem, restricoes_alimentares, nivel_caminhada,
	  horarios_preferidos, aversoes, clima_desejado, datas_flexiveis, cidades_proximas
	"""
	interesses = data.get("interesses", []) or []
	interesses_str = ", ".join(interesses)
	data_inicio_fmt = _fmt_date_safe(data.get("data_inicio"))
	return f"""
# TAREFA PRINCIPAL: CRIAR UM ROTEIRO DE VIAGEM DETALHADO E PERSONALIZADO EM JSON

Você está prestes a criar o roteiro de viagem mais completo e personalizado possível. Siga estas diretrizes para garantir a melhor experiência:

1. **Seja extremamente detalhado** - Inclua descrições ricas, dicas locais, histórias interessantes e informações práticas.
2. **Personalize profundamente** - Adapte cada sugestão ao perfil exato dos viajantes.
3. **Forneça contexto** - Explique o porquê de cada recomendação e o que a torna especial.
4. **Seja prático** - Inclua dicas de transporte, horários ideais, tempo médio de visita e orçamentos.
5. **Antecipe necessidades** - Considere o cansaço, necessidades especiais e preferências dos viajantes.

Sua resposta DEVE ser APENAS um JSON válido com a estrutura exata fornecida.

## DADOS DA VIAGEM FORNECIDOS
* **Destino Principal:** {data.get('destino')}
* **Período da Viagem:** {data.get('periodo_especifico')}
* **Duração Total:** {data.get('duracao')} dias
* **Tipo de Data:** {data.get('tipo_data')}
* **Perfil dos Viajantes:** {data.get('perfil')}
* **Orçamento (Estilo):** {data.get('orcamento')}
* **Interesses Chave:** {interesses_str}
* **Ritmo da Viagem Desejado:** {data.get('ritmo')}
* **Número de Viajantes:** {data.get('num_viajantes')}
* **Faixa Etária:** {data.get('faixa_etaria')}
* **Leva Crianças?:** {"Sim" if data.get('criancas') else "Não"}
* **Preferência de Hospedagem:** {data.get('hospedagem')}
* **Restrições Alimentares:** {data.get('restricoes_alimentares')}
* **Nível de Caminhada:** {data.get('nivel_caminhada')}
* **Horários Preferidos:** {data.get('horarios_preferidos')}
* **Aversões (evitar):** {data.get('aversoes')}
* **Clima Desejado:** {data.get('clima_desejado')}
* **Datas Flexíveis?:** {data.get('datas_flexiveis')}
* **Cidades Próximas de Interesse:** {data.get('cidades_proximas')}
* **Observações e Pedidos Especiais:** {data.get('observacoes')}

## ESTRUTURA DE SAÍDA OBRIGATÓRIA (JSON EXATO)

Retorne APENAS este JSON (sem markdown, sem texto adicional):

{{
  "titulo": "Plano de Exploração para {data.get('destino')}",
  "subtitulo": "Aqui está o seu plano de aventura personalizado para {data.get('destino')}, desenhado especialmente para um(a) {data.get('perfil')} com foco em {interesses_str}. Prepare-se para uma experiência inesquecível!",
  "visao_geral": {{
    "destino": "{data.get('destino')}",
    "duracao": {data.get('duracao')},
    "estilo": "{data.get('orcamento')} e {data.get('ritmo')}",
    "periodo_escolhido": "Descreva o período escolhido e por que é ideal para este destino",
    "clima_esperado": "Descrição do clima esperado para a época escolhida",
    "hospedagem_sugerida": "Sugestões de hospedagem baseadas no perfil e época"
  }},
  "cronograma": [
    {{
      "dia": 1,
      "titulo": "Imersão Inicial e Sabores Locais",
      "atividades": [
        {{
          "horario": "Manhã (09:00 - 12:00)",
          "atividade": "Chegada, acomodação e primeira caminhada de reconhecimento pelo bairro do hotel.",
          "dica": ""
        }},
        {{
          "horario": "Tarde (14:00 - 18:00)",
          "atividade": "Atividade leve e impactante, alinhada aos interesses. Ex: Visita ao mercado central para um mergulho na cultura gastronômica local.",
          "dica": ""
        }},
        {{
          "horario": "Noite (20:00 onwards)",
          "atividade": "Jantar de boas-vindas. Opção casual e uma mais elaborada.",
          "dica": ""
        }},
        {{
          "horario": "Pós-jantar (22:00 onwards)",
          "atividade": "Exploração da vida noturna local. Sugira bares, festas, shows ou eventos noturnos baseados nos interesses do viajante.",
          "dica": "Verifique horários de funcionamento e dress code dos locais"
        }}
      ]
    }}
  ],
  "gastronomia": {{
    "pratos_indispensaveis": [
      "Liste 3 a 5 pratos/bebidas típicos que o viajante precisa provar"
    ],
    "restaurante_tesouro": "Sugira um restaurante excelente e menos turístico",
    "experiencia_culinaria": "Sugira uma aula de culinária, um tour gastronômico ou algo similar"
  }},
  "vida_noturna": {{
    "bares_recomendados": [
      "Liste 3-5 bares, pubs ou lounges imperdíveis"
    ],
    "clubes_festas": [
      "Sugira clubes, discotecas ou locais de festa"
    ],
    "shows_eventos": [
      "Mencione shows, concertos ou eventos noturnos especiais"
    ],
    "roteiro_bar_hopping": "Sugira um roteiro de bar hopping ou experiência noturna única",
    "dicas_noturnas": "Dicas específicas para a vida noturna (horários, dress code, segurança)"
  }},
  "dicas_viagem": {{
    "mobilidade": "A melhor forma de se locomover: transporte público, app de carros, a pé, etc.",
    "comunicacao": "Uma frase útil no idioma local e dicas sobre conectividade/SIM card",
    "alerta_especialista": "Uma dica crucial de segurança, etiqueta cultural ou um hack de viagem para este destino específico"
  }}
}}

IMPORTANTE: 
- Complete o cronograma para todos os {data.get('duracao')} dias
- Use títulos criativos para cada dia
- Inclua dicas práticas quando relevante
- Seja específico e detalhado
- **ESCOLHA DE DATAS INTELIGENTE**:
  * Se "Data específica" foi escolhida: use a data exata fornecida
  * Se "Mês e ano" foi escolhida: escolha os MELHORES dias daquele mês para o destino (considerando clima, eventos, temporada alta/baixa)
  * Se "Melhor período" foi escolhida: selecione a MELHOR época do ano para visitar o destino (considerando clima, eventos, preços, crowds)
- **VIDA NOTURNA ESPECIAL**: Se "Vida noturna" estiver nos interesses, inclua atividades noturnas detalhadas como:
  * Bares temáticos, pubs, lounges
  * Festas, clubes, discotecas
  * Shows ao vivo, concertos, apresentações
  * Eventos noturnos especiais (festivais, feiras noturnas)
  * Roteiros de bar hopping
  * Experiências noturnas únicas do destino
- Para cada dia, inclua pelo menos uma atividade noturna (22:00+) se vida noturna for um interesse
- **CLIMA E ÉPOCA**: Sempre considere o clima ideal, eventos sazonais e temporadas do destino
- Retorne APENAS o JSON, sem texto adicional
"""
