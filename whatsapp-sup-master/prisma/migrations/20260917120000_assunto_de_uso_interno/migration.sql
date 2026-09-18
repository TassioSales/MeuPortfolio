-- Assunto de uso interno: a categoria que a TI usa para classificar, mas que o
-- bot nunca oferece no menu do WhatsApp.
--
-- Ate aqui, `ativa` era o unico interruptor de uma categoria, e ele nao separava
-- as duas perguntas que a equipe faz na pratica: "esse assunto ainda existe?" e
-- "esse assunto pode ser escolhido pelo cliente?". Quem quisesse um assunto so
-- de uso interno tinha de desativa-lo - e ai ele sumia TAMBEM do seletor do
-- painel, que e justamente onde ele precisava estar.
--
-- Por isso a coluna e um segundo eixo e nao um terceiro valor de `ativa`:
--   `ativa = 1, visivelNoWhatsapp = 1` -> assunto normal, no menu e no painel;
--   `ativa = 1, visivelNoWhatsapp = 0` -> assunto interno, so no painel;
--   `ativa = 0`                        -> fora de circulacao nos dois lugares,
--                                         preservado nos chamados antigos.
--
-- `DEFAULT true` e o que faz esta migracao nao precisar de UPDATE: toda
-- categoria que existia antes desta coluna era oferecida no menu, entao o padrao
-- ja descreve o estado correto de todas elas.
--
-- `ALTER TABLE ADD COLUMN` puro, sem reconstruir a tabela: o SQLite aceita
-- coluna NOT NULL nova quando o default e uma constante, e nao ha tipo a mudar.
--
-- A view `chamados_para_cards` NAO precisa sair e voltar aqui (ao contrario das
-- migracoes que mexeram em `Chamado`): ela le `Chamado`, e a unica coisa que
-- guarda de categoria e o `categoriaId`. Esta migracao nao toca em `Chamado`.
ALTER TABLE "Categoria" ADD COLUMN "visivelNoWhatsapp" BOOLEAN NOT NULL DEFAULT true;

-- O indice do menu passa a cobrir as duas igualdades do filtro. Trocar em vez de
-- somar um segundo: a consulta que monta o menu e uma so, e manter o antigo
-- deixaria um indice que nenhuma consulta usa inteiro.
DROP INDEX IF EXISTS "Categoria_ativa_ordem_idx";
CREATE INDEX "Categoria_ativa_visivelNoWhatsapp_ordem_idx" ON "Categoria"("ativa", "visivelNoWhatsapp", "ordem");
