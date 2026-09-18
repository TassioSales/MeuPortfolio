-- Liga o perfil de Pessoa a quem entrou pelo Entra ID.
--
-- Ate aqui, login e cadastro de pessoas nao se conheciam: quem entrava recebia
-- um cookie de sessao, e o cadastro so crescia pelo botao "+ Adicionar pessoa".
-- Resultado pratico - duas pessoas ja tinham entrado no painel e o seletor de
-- "Responsavel" continuava vazio.
--
-- `oid` e o identificador do usuario no diretorio da Microsoft, e e por ele que
-- o login reencontra o perfil. Casar por e-mail criaria um perfil novo a cada
-- mudanca de nome de dominio ou correcao de grafia, e os chamados ficariam
-- apontando para o antigo.
--
-- As duas colunas sao OPCIONAIS: quem foi cadastrado a mao continua sem oid, e
-- isso e um estado legitimo - atendente sem conta no dominio, ou perfil criado
-- antes do primeiro login.
--
-- `ALTER TABLE ADD COLUMN` puro (sem reconstruir a tabela) porque coluna nova
-- anulavel nao exige: nao ha default a preencher nem tipo a mudar.
ALTER TABLE "Pessoa" ADD COLUMN "oid" TEXT;
ALTER TABLE "Pessoa" ADD COLUMN "email" TEXT;

-- Um oid por perfil. Sem isto, dois logins simultaneos da mesma pessoa (duas
-- abas, dois dispositivos) criariam dois perfis, e o `upsert` da rota nao teria
-- como saber qual e o dela.
--
-- Indice UNIQUE e nao constraint: no SQLite, `NULL` nunca colide com `NULL`,
-- entao os cadastrados a mao continuam podendo ser muitos.
CREATE UNIQUE INDEX "Pessoa_oid_key" ON "Pessoa"("oid");
