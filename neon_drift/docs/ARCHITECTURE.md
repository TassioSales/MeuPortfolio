# Architecture

Neon Drift e single-player, mas tem backend.

O backend nao controla movimento em tempo real. Ele cuida de:

- servir o frontend;
- expor configuracao de jogo;
- receber pontuacoes;
- manter leaderboard em memoria;
- fornecer ponto de evolucao para banco de dados, autenticacao e conquistas.

Essa divisao evita complexidade multiplayer, mas ainda treina uma arquitetura full-stack real.
