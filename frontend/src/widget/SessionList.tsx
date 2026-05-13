// Vue "liste" du widget : conversations récentes + bouton nouvelle.

import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import type { ChatSession } from "../api/types";

interface Props {
  onSelect: (id: string) => void;
  onNew: () => void;
  refreshKey: number;
}

export default function SessionList({ onSelect, onNew, refreshKey }: Props) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listSessions()
      .then((s) => !cancelled && setSessions(s))
      .catch(() => !cancelled && setSessions([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (!confirm("Supprimer cette conversation ?")) return;
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Erreur");
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <button
        onClick={onNew}
        className="w-full flex items-center gap-3 p-4 hover:bg-slate-50 border-b border-slate-100 transition"
      >
        <span className="w-9 h-9 rounded-full bg-brand-600 text-white flex items-center justify-center text-lg shrink-0">
          +
        </span>
        <span className="text-left">
          <span className="block font-medium text-slate-800">Nouvelle question</span>
          <span className="block text-xs text-slate-500">Démarrer une conversation</span>
        </span>
      </button>

      {loading && (
        <p className="p-4 text-sm text-slate-400 text-center">Chargement...</p>
      )}

      {!loading && sessions.length === 0 && (
        <div className="p-6 text-center text-slate-400 text-sm">
          <p>Aucune conversation pour le moment.</p>
          <p className="mt-1">Cliquez ci-dessus pour commencer 👆</p>
        </div>
      )}

      {sessions.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className="group w-full text-left px-4 py-3 hover:bg-slate-50 border-b border-slate-100 transition flex items-start gap-3"
        >
          <span className="w-9 h-9 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center text-lg shrink-0">
            💬
          </span>
          <span className="flex-1 min-w-0">
            <span className="block truncate text-sm font-medium text-slate-800">
              {s.title}
            </span>
            <span className="block text-xs text-slate-500 mt-0.5">
              {s.status === "ended" ? "Terminée" : "En cours"}
              {s.rating !== null && ` • ${"⭐".repeat(s.rating)}`}
            </span>
          </span>
          <button
            onClick={(e) => handleDelete(e, s.id)}
            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition text-xs"
            title="Supprimer"
          >
            ✕
          </button>
        </button>
      ))}
    </div>
  );
}
