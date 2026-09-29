"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { Textarea } from "@/components/Textarea";
import { messageFrom } from "@/hooks/useAgents";
import {
  atualizarModelo,
  criarModelo,
  excluirModelo,
  listarModelos,
  listarVariaveis,
} from "@/lib/contratos";
import type { ModeloDeContrato, VariavelDeContrato } from "@/types";

/**
 * Os modelos de contrato.
 *
 * O texto é escrito aqui, pelo advogado, e não no código. Não é preguiça de
 * quem programou: as cláusulas — e principalmente o percentual de honorários —
 * são compromisso comercial e profissional do escritório. Um número embutido
 * no software viraria obrigação assumida em nome de alguém que nunca a
 * escolheu.
 *
 * O que o sistema faz é trocar `{{cliente.nome}}` por um nome. A lista de
 * lacunas vem do backend, para não haver duas listas que possam divergir.
 */

const VAZIO = { nome: "", corpo: "", ativo: false };

/** O que ainda não foi coletado sai assim no contrato. */
const LACUNA = "____________";

export default function ContratosPage() {
  const [modelos, setModelos] = useState<ModeloDeContrato[]>([]);
  const [variaveis, setVariaveis] = useState<VariavelDeContrato[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  /** `null` = nenhum em edição; `""` = criando um novo. */
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [rascunho, setRascunho] = useState(VAZIO);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [lista, vars] = await Promise.all([listarModelos(), listarVariaveis()]);
      setModelos(lista);
      setVariaveis(vars);
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os modelos."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function abrirNovo() {
    setEditandoId("");
    setRascunho(VAZIO);
    setErro(null);
    setSalvo(false);
  }

  function abrirEdicao(modelo: ModeloDeContrato) {
    setEditandoId(modelo.id);
    setRascunho({ nome: modelo.nome, corpo: modelo.corpo, ativo: modelo.ativo });
    setErro(null);
    setSalvo(false);
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setSalvando(true);
    setErro(null);
    setSalvo(false);
    try {
      if (editandoId) {
        await atualizarModelo(editandoId, rascunho);
      } else {
        await criarModelo(rascunho);
      }
      setEditandoId(null);
      setSalvo(true);
      await carregar();
    } catch (e) {
      // A mensagem do backend nomeia a variável escrita errada; trocá-la por
      // um texto genérico apagaria a única informação útil.
      setErro(messageFrom(e, "Não foi possível salvar o modelo."));
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(modelo: ModeloDeContrato) {
    const confirmado = window.confirm(
      `Apagar o modelo "${modelo.nome}"? Os contratos já emitidos continuam como estão.`,
    );
    if (!confirmado) return;

    try {
      await excluirModelo(modelo.id);
      if (editandoId === modelo.id) setEditandoId(null);
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível apagar o modelo."));
    }
  }

  if (carregando) return <FullPageLoader label="Carregando modelos..." />;

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-fg">Modelos de contrato</h1>
          <p className="mt-1 max-w-2xl text-sm text-fg-muted">
            O texto é seu. O sistema só troca as lacunas pelos dados do cliente —
            não escreve cláusula nem define honorários.
          </p>
        </div>
        {editandoId === null && <Button onClick={abrirNovo}>Novo modelo</Button>}
      </header>

      {erro && (
        <p
          role="alert"
          className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
        >
          {erro}
        </p>
      )}
      {salvo && (
        <p role="status" className="mb-4 text-sm text-green-700 dark:text-green-300">
          Modelo salvo.
        </p>
      )}

      {editandoId !== null ? (
        <form onSubmit={enviar} className="flex flex-col gap-5">
          <fieldset className="rounded-xl border border-surface-border bg-surface p-5">
            <legend className="px-2 text-sm font-medium text-fg">
              {editandoId ? "Editar modelo" : "Novo modelo"}
            </legend>

            <div className="flex flex-col gap-4">
              <Input
                label="Nome do modelo"
                maxLength={255}
                required
                value={rascunho.nome}
                onChange={(e) =>
                  setRascunho((r) => ({ ...r, nome: e.target.value }))
                }
              />

              <Textarea
                label="Texto do contrato"
                rows={22}
                required
                className="min-h-[28rem] font-mono text-xs"
                hint="Linha começando com # vira título centralizado. **texto** fica em negrito."
                value={rascunho.corpo}
                onChange={(e) =>
                  setRascunho((r) => ({ ...r, corpo: e.target.value }))
                }
              />

              <label className="flex items-start gap-2.5 text-sm text-fg">
                <input
                  type="checkbox"
                  // `bg-` e `accent-` explícitos: sem eles o navegador pinta a
                  // caixa com o padrão dele (branco e azul), que no tema
                  // escuro destoa de tudo à volta.
                  className="mt-0.5 h-4 w-4 rounded border-surface-border bg-surface accent-ink-900 dark:accent-ink-100"
                  checked={rascunho.ativo}
                  onChange={(e) =>
                    setRascunho((r) => ({ ...r, ativo: e.target.checked }))
                  }
                />
                <span>
                  Usar este modelo nos contratos novos
                  <span className="mt-0.5 block text-xs text-fg-muted">
                    Só um fica ativo por vez — ativar este desativa o anterior.
                  </span>
                </span>
              </label>
            </div>
          </fieldset>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" isLoading={salvando}>
              {salvando ? "Salvando..." : "Salvar"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditandoId(null)}
            >
              Cancelar
            </Button>
          </div>
        </form>
      ) : (
        <ul className="flex flex-col gap-2">
          {modelos.length === 0 && (
            <li className="rounded-xl border border-dashed border-surface-border p-8 text-center text-sm text-fg-muted">
              Nenhum modelo ainda. Crie um com o texto do seu contrato de
              honorários — as lacunas estão listadas abaixo.
            </li>
          )}
          {modelos.map((modelo) => (
            <li
              key={modelo.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-border bg-surface px-4 py-3"
            >
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-sm font-medium text-fg">
                  {modelo.nome}
                  {modelo.ativo && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/50 dark:text-green-200">
                      em uso
                    </span>
                  )}
                </p>
                <p className="mt-0.5 text-xs text-fg-muted">
                  {modelo.corpo.length.toLocaleString("pt-BR")} caracteres
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="px-3 py-1.5"
                  onClick={() => abrirEdicao(modelo)}
                >
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  className="px-3 py-1.5"
                  onClick={() => excluir(modelo)}
                >
                  Apagar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <section className="mt-8 rounded-xl border border-surface-border bg-surface-muted p-5">
        <h2 className="text-sm font-medium text-fg">Lacunas que você pode usar</h2>
        <p className="mt-1 text-xs text-fg-muted">
          Escreva entre chaves duplas. O que o escritório ainda não tiver
          coletado sai como <code className="font-mono">{LACUNA}</code> no
          contrato — em branco, para quem lê reparar.
        </p>
        <dl className="mt-4 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {variaveis.map((v) => (
            <div key={v.nome} className="flex flex-wrap items-baseline gap-2">
              <dt className="font-mono text-xs text-fg">{`{{${v.nome}}}`}</dt>
              <dd className="text-xs text-fg-muted">{v.descricao}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
