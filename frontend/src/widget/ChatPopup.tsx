// Conteneur du popup : header + vue active (liste ou chat).
// Bascule entre les deux vues via un état local.

import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import ChatView from "./ChatView";
import SessionList from "./SessionList";

interface Props {
  onClose: () => void;
}

export default function ChatPopup({ onClose }: Props) {
  const { user, logout } = useAuth();
  const [view, setView] = useState<"list" | "chat">("list");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  function openSession(id: string) {
    setCurrentSessionId(id);
    setView("chat");
  }

  function newConversation() {
    setCurrentSessionId(null);
    setView("chat");
  }

  function backToList() {
    setView("list");
    setRefreshKey((k) => k + 1); // refresh la liste avec les MAJ (titre, status...)
  }

  return (
    <div className="fixed bottom-24 right-5 z-30 w-[calc(100vw-2.5rem)] max-w-[400px] h-[600px] max-h-[calc(100vh-7rem)] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-200 animate-[slideup_0.2s_ease-out]">
      {/* Header */}
      <header className="bg-brand-600 text-white px-4 py-3 flex items-center gap-3">
        {view === "chat" && (
          <button
            onClick={backToList}
            aria-label="Retour"
            className="hover:bg-white/10 rounded p-1 transition"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-sm">Assistant Finance</h2>
          <p className="text-xs text-brand-50/80">
            {view === "list"
              ? user?.is_anonymous
                ? "Mode invité"
                : `Connecté en tant que ${user?.name || user?.email}`
              : "RAG + recherche web"}
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Fermer"
          className="hover:bg-white/10 rounded p-1 transition"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      {/* Banner connexion (uniquement en mode anonyme et vue liste) */}
      {view === "list" && user?.is_anonymous && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-900">
          💡 <Link to="/login" className="underline font-medium">Connectez-vous</Link>{" "}
          pour conserver vos conversations entre vos appareils.
        </div>
      )}

      {/* Contenu */}
      {view === "list" ? (
        <SessionList
          onSelect={openSession}
          onNew={newConversation}
          refreshKey={refreshKey}
        />
      ) : (
        <ChatView
          sessionId={currentSessionId}
          onSessionChange={setCurrentSessionId}
          onSessionRefreshed={() => setRefreshKey((k) => k + 1)}
        />
      )}

      {/* Footer (uniquement vue liste, pour logout) */}
      {view === "list" && !user?.is_anonymous && (
        <div className="border-t border-slate-200 px-4 py-2 text-xs text-center">
          <button onClick={logout} className="text-slate-500 hover:text-slate-700">
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}
