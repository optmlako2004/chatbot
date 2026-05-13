import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { ChatSession } from "../api/types";

interface Props {
  currentSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  refreshKey: number; // change quand on veut forcer un refresh externe
}

export default function Sidebar({
  currentSessionId,
  onSelect,
  onNew,
  refreshKey,
}: Props) {
  const { user, logout } = useAuth();
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
      if (currentSessionId === id) onNew();
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Erreur");
    }
  }

  return (
    <aside className="w-72 bg-slate-900 text-slate-100 flex flex-col h-full">
      <div className="p-4 border-b border-slate-800">
        <button
          onClick={onNew}
          className="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-2 rounded-lg transition flex items-center justify-center gap-2"
        >
          <span className="text-lg leading-none">+</span> Nouvelle conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        <h3 className="px-2 text-xs uppercase font-semibold text-slate-400 mb-2">
          Conversations
        </h3>

        {loading && (
          <p className="px-2 text-sm text-slate-400">Chargement...</p>
        )}
        {!loading && sessions.length === 0 && (
          <p className="px-2 text-sm text-slate-400">Aucune conversation.</p>
        )}

        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`group w-full text-left px-3 py-2 rounded-lg transition flex items-start gap-2 ${
              currentSessionId === s.id
                ? "bg-slate-700"
                : "hover:bg-slate-800"
            }`}
          >
            <span className="flex-1 min-w-0">
              <span className="block truncate text-sm font-medium">
                {s.title}
              </span>
              <span className="block text-xs text-slate-400 mt-0.5">
                {s.status === "ended" ? "Terminée" : "En cours"}
                {s.rating !== null && ` • ${"⭐".repeat(s.rating)}`}
              </span>
            </span>
            <button
              onClick={(e) => handleDelete(e, s.id)}
              className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-400 text-xs transition"
              title="Supprimer"
            >
              ✕
            </button>
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-slate-800">
        {user && (
          <div className="flex items-center gap-3 mb-3">
            {user.picture ? (
              <img
                src={user.picture}
                alt=""
                className="w-9 h-9 rounded-full"
              />
            ) : (
              <div className="w-9 h-9 rounded-full bg-brand-600 flex items-center justify-center text-sm font-bold">
                {(user.name?.[0] || user.email?.[0] || "?").toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user.name || user.email || "Anonyme"}
              </p>
              <p className="text-xs text-slate-400 truncate">
                {user.is_anonymous ? "Mode anonyme" : user.email}
              </p>
            </div>
          </div>
        )}
        {user?.is_anonymous ? (
          <a
            href="/login"
            className="block text-center text-sm text-brand-300 hover:text-brand-200 underline"
          >
            Se connecter pour sauvegarder
          </a>
        ) : (
          <button
            onClick={logout}
            className="w-full text-sm text-slate-300 hover:text-white py-1"
          >
            Déconnexion
          </button>
        )}
      </div>
    </aside>
  );
}
