#!/usr/bin/env python3
"""
Exemplos de uso do Gerador de Roteiros de Viagem com IA
"""

from utils.prompts import format_user_prompt_viagem, SYSTEM_PROMPT_VIAGEM
from datetime import date

def exemplo_viagem_romantica():
    """Exemplo de dados para uma viagem romântica"""
    return {
        "destino": "Paris, França",
        "data_inicio": date(2024, 6, 15),
        "duracao": 5,
        "perfil": "Casal",
        "orcamento": "Luxo",
        "interesses": ["Gastronomia", "Arte e museus", "História"],
        "ritmo": "Relaxado",
        "observacoes": "Aniversário de casamento, queremos algo especial",
        "num_viajantes": 2,
        "criancas": False,
        "faixa_etaria": "26-35",
        "hospedagem": "Hotel 5*",
        "restricoes_alimentares": "Nenhuma",
        "nivel_caminhada": "Médio",
        "horarios_preferidos": "Acordar tarde, jantar romântico",
        "aversoes": "Locais muito turísticos",
        "clima_desejado": "Ameno",
        "datas_flexiveis": "Não",
        "cidades_proximas": "Versailles, Giverny",
        "tipo_data": "Data específica (dia/mês/ano)",
        "data_flexivel": False,
        "periodo_especifico": "Data específica: 15/06/2024"
    }

def exemplo_viagem_familia():
    """Exemplo de dados para uma viagem em família"""
    return {
        "destino": "Orlando, EUA",
        "data_inicio": date(2024, 7, 1),
        "duracao": 10,
        "perfil": "Família",
        "orcamento": "Intermediário",
        "interesses": ["Aventura", "Tecnologia", "Natureza"],
        "ritmo": "Moderado",
        "observacoes": "Viagem com crianças de 8 e 12 anos, queremos parques temáticos",
        "num_viajantes": 4,
        "criancas": True,
        "faixa_etaria": "26-35",
        "hospedagem": "Hotel 4*",
        "restricoes_alimentares": "Uma criança é vegetariana",
        "nivel_caminhada": "Alto",
        "horarios_preferidos": "Acordar cedo para aproveitar os parques",
        "aversoes": "Filas muito longas",
        "clima_desejado": "Quente",
        "datas_flexiveis": "Sim",
        "cidades_proximas": "Miami, Tampa",
        "tipo_data": "Mês e ano",
        "data_flexivel": True,
        "periodo_especifico": "Mês e ano: Julho de 2024"
    }

def exemplo_viagem_aventura():
    """Exemplo de dados para uma viagem de aventura"""
    return {
        "destino": "Nepal",
        "data_inicio": date(2024, 10, 1),
        "duracao": 14,
        "perfil": "Grupo de amigos",
        "orcamento": "Econômico",
        "interesses": ["Aventura", "Natureza", "História"],
        "ritmo": "Intenso",
        "observacoes": "Trekking no Himalaia, queremos desafios físicos",
        "num_viajantes": 6,
        "criancas": False,
        "faixa_etaria": "26-35",
        "hospedagem": "Hostel",
        "restricoes_alimentares": "Nenhuma",
        "nivel_caminhada": "Alto",
        "horarios_preferidos": "Acordar cedo para trekking",
        "aversoes": "Locais muito caros",
        "clima_desejado": "Frio",
        "datas_flexiveis": "Sim",
        "cidades_proximas": "Katmandu, Pokhara",
        "tipo_data": "Melhor período (IA escolhe)",
        "data_flexivel": True,
        "periodo_especifico": "Melhor período para o destino (IA escolherá as datas ideais)"
    }

def exemplo_viagem_negocios():
    """Exemplo de dados para uma viagem de negócios"""
    return {
        "destino": "São Paulo, Brasil",
        "data_inicio": date(2024, 9, 15),
        "duracao": 3,
        "perfil": "Negócios",
        "orcamento": "Intermediário",
        "interesses": ["Tecnologia", "Gastronomia"],
        "ritmo": "Intenso",
        "observacoes": "Reuniões durante o dia, queremos aproveitar a noite",
        "num_viajantes": 1,
        "criancas": False,
        "faixa_etaria": "36-50",
        "hospedagem": "Hotel 4*",
        "restricoes_alimentares": "Nenhuma",
        "nivel_caminhada": "Baixo",
        "horarios_preferidos": "Flexível",
        "aversoes": "Locais muito barulhentos",
        "clima_desejado": "Ameno",
        "datas_flexiveis": "Não",
        "cidades_proximas": "Santos, Campinas",
        "tipo_data": "Data específica (dia/mês/ano)",
        "data_flexivel": False,
        "periodo_especifico": "Data específica: 15/09/2024"
    }

def demonstrar_formatacao():
    """Demonstra como formatar dados para a IA"""
    print("🗺️ EXEMPLOS DE DADOS PARA O GERADOR DE ROTEIROS")
    print("=" * 60)
    
    exemplos = [
        ("Viagem Romântica", exemplo_viagem_romantica()),
        ("Viagem em Família", exemplo_viagem_familia()),
        ("Viagem de Aventura", exemplo_viagem_aventura()),
        ("Viagem de Negócios", exemplo_viagem_negocios())
    ]
    
    for nome, dados in exemplos:
        print(f"\n📋 {nome.upper()}")
        print("-" * 40)
        print(f"Destino: {dados['destino']}")
        print(f"Duração: {dados['duracao']} dias")
        print(f"Perfil: {dados['perfil']}")
        print(f"Orçamento: {dados['orcamento']}")
        print(f"Interesses: {', '.join(dados['interesses'])}")
        print(f"Ritmo: {dados['ritmo']}")
        print(f"Observações: {dados['observacoes']}")
        
        # Demonstra a formatação do prompt
        prompt = format_user_prompt_viagem(dados)
        print(f"\n📝 Prompt gerado ({len(prompt)} caracteres):")
        print(prompt[:200] + "..." if len(prompt) > 200 else prompt)

def main():
    """Função principal para demonstrar os exemplos"""
    print("🚀 DEMONSTRAÇÃO DO GERADOR DE ROTEIROS")
    print("=" * 60)
    
    # Mostra o prompt do sistema
    print("\n🤖 PROMPT DO SISTEMA:")
    print("-" * 40)
    print(SYSTEM_PROMPT_VIAGEM[:300] + "...")
    
    # Demonstra os exemplos
    demonstrar_formatacao()
    
    print("\n" + "=" * 60)
    print("✅ Demonstração concluída!")
    print("💡 Use estes exemplos como base para seus próprios roteiros")
    print("=" * 60)

if __name__ == "__main__":
    main()
