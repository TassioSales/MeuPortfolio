"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { deleteNote, fetchGraph, fetchNotes } from "@/lib/api";
import { useGraphSocket } from "@/lib/ws";
import type { GraphData, GraphNode, Note } from "@/lib/types";
import NoteEditor from "@/components/NoteEditor";
import NodePanel from "@/components/NodePanel";

// GraphView uses D3 which requires the browser — disable SSR
const GraphView = dynamic(() => import("@/components/GraphView"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center w-full h-full">
      <p className="text-[#8b949e] text-sm">Carregando grafo…</p>
    </div>
  ),
});

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8080/ws";

type RightPanel = "editor" | "node";

export default function HomePage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNote, setSelectedNote] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [rightPanel, setRightPanel] = useState<RightPanel>("editor");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Real-time graph updates via WebSocket
  const wsGraph = useGraphSocket(WS_URL);

  // Initial data load
  useEffect(() => {
    void loadNotes();
    void loadGraph();
  }, []);

  // Apply WS graph updates
  useEffect(() => {
    if (wsGraph) setGraphData(wsGraph);
  }, [wsGraph]);

  async function loadNotes() {
    try {
      const data = await fetchNotes();
      setNotes(data ?? []);
    } catch (err) {
      console.error("loadNotes:", err);
    }
  }

  async function loadGraph() {
    try {
      const data = await fetchGraph();
      setGraphData(data);
    } catch (err) {
      console.error("loadGraph:", err);
    }
  }

  const handleNoteSaved = useCallback(async () => {
    await loadNotes();
    // Graph is updated via WS broadcast from the Go API
  }, []);

  async function handleDeleteNote(id: number) {
    setDeletingId(id);
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
      if (selectedNote === id) setSelectedNote(null);
    } catch (err) {
      console.error("deleteNote:", err);
    } finally {
      setDeletingId(null);
    }
  }

  function handleNodeClick(node: GraphNode) {
    setSelectedNode(node);
    setRightPanel("node");
  }

  function handleNewNote() {
    setRightPanel("editor");
    setSelectedNode(null);
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ---- Left sidebar: note list ---- */}
      <aside className="w-[22%] min-w-[180px] flex flex-col bg-[#161b22] border-r border-[#30363d]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#30363d]">
          <span className="text-[#e6edf3] font-semibold text-sm tracking-wide">
            MemMap
          </span>
          <button
            onClick={handleNewNote}
            className="text-xs bg-[#238636] hover:bg-[#2ea043] text-white px-2.5 py-1 rounded-md transition-colors font-medium"
          >
            + Nova
          </button>
        </div>

        {/* Note count */}
        <div className="px-4 py-2 border-b border-[#30363d]">
          <span className="text-[#8b949e] text-xs">
            {notes.length} nota{notes.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Notes list */}
        <ul className="flex-1 overflow-y-auto">
          {notes.length === 0 ? (
            <li className="px-4 py-8 text-center text-[#8b949e] text-xs">
              Nenhuma nota ainda.
              <br />
              Crie sua primeira nota!
            </li>
          ) : (
            notes.map((note) => (
              <li
                key={note.id}
                className={`group border-b border-[#30363d] px-3 py-2 cursor-pointer transition-colors ${
                  selectedNote === note.id
                    ? "bg-[#1f2937]"
                    : "hover:bg-[#1c2128]"
                }`}
                onClick={() => setSelectedNote(note.id)}
              >
                <div className="flex items-start justify-between gap-1">
                  <p className="text-[#e6edf3] text-xs font-medium line-clamp-1 flex-1">
                    {note.title}
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleDeleteNote(note.id);
                    }}
                    disabled={deletingId === note.id}
                    className="opacity-0 group-hover:opacity-100 text-[#8b949e] hover:text-red-400 text-xs transition-all leading-none ml-1"
                    aria-label="Deletar nota"
                  >
                    {deletingId === note.id ? "…" : "×"}
                  </button>
                </div>
                <p className="text-[#8b949e] text-[10px] mt-0.5 line-clamp-1">
                  {note.content}
                </p>
                <p className="text-[#8b949e] text-[10px] mt-0.5">
                  {new Date(note.updated_at).toLocaleDateString("pt-BR")}
                </p>
              </li>
            ))
          )}
        </ul>
      </aside>

      {/* ---- Center: Knowledge Graph ---- */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center px-4 py-2 border-b border-[#30363d] bg-[#161b22]">
          <h1 className="text-[#e6edf3] text-sm font-medium">
            Grafo de Conhecimento
          </h1>
          <span className="ml-auto text-[#8b949e] text-xs">
            {graphData.nodes.length} nós · {graphData.links.length} conexões
          </span>
        </div>
        <div className="flex-1 relative">
          <GraphView data={graphData} onNodeClick={handleNodeClick} />
        </div>
      </main>

      {/* ---- Right panel: Note Editor or Node Details ---- */}
      <aside className="w-[26%] min-w-[220px] flex flex-col bg-[#161b22] border-l border-[#30363d] p-4">
        {rightPanel === "editor" ? (
          <NoteEditor onSaved={handleNoteSaved} />
        ) : selectedNode ? (
          <NodePanel
            node={selectedNode}
            notes={notes}
            onClose={handleNewNote}
          />
        ) : (
          <NoteEditor onSaved={handleNoteSaved} />
        )}
      </aside>
    </div>
  );
}
