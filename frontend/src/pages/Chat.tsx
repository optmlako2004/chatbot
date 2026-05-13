// Page principale : sidebar + zone de chat.
//
// Comportements clés :
// - Au montage, si une conversation est sélectionnée, on appelle
//   GET /sessions/{id}/messages → l'historique survit au refresh.
// - Quand on envoie un message : POST /sessions/{id}/chat, on attend
//   la réponse et on l'ajoute au flux.
// - Inactivité 2 min → InactivityModal (Continuer / Terminer).
// - Fin de session → message de farewell injecté + FeedbackModal.

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api/client";
import type { ChatMessage, ChatSession } from "../api/types";
import ChatInput from "../components/ChatInput";
import FeedbackModal from "../components/FeedbackModal";
import InactivityModal from "../components/InactivityModal";
import MessageBubble from "../components/MessageBubble";
import Sidebar from "../components/Sidebar";
import { useInactivity } from "../hooks/useInactivity";

const INACTIVITY_MS = 2 * 60 * 1000; // 2 minutes

export default function Chat() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showInactivity, setShowInactivity] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll en bas à chaque nouveau message
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, sending]);

  // Au changement de session : recharge les messages depuis le backend
  useEffect(() => {
    if (!currentSessionId) {
      setCurrentSession(null);
      setMessages([]);
      return;
    }
    let cancelled = false;
    Promise.all([
      api.getSession(currentSessionId),
      api.getMessages(currentSessionId),
    ])
      .then(([sess, msgs]) => {
        if (cancelled) return;
        setCurrentSession(sess);
        setMessages(msgs);
        setError(null);
      })
      .catch(() => !cancelled && setError("Conversation introuvable."));
    return () => {
      cancelled = true;
    };
  }, [currentSessionId]);

  // Détection d'inactivité (active uniquement si conversation active)
  const inactivityEnabled =
    currentSession?.status === "active" && !showInactivity && !showFeedback;
  useInactivity(INACTIVITY_MS, () => setShowInactivity(true), inactivityEnabled);

  async function handleNew() {
    try {
      const sess = await api.createSession();
      setCurrentSessionId(sess.id);
      setSidebarRefresh((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur");
    }
  }

  async function handleSend(text: string) {
    let sessionId = currentSessionId;
    // Si aucune conversation : on en crée une à la volée
    if (!sessionId) {
      const sess = await api.createSession();
      sessionId = sess.id;
      setCurrentSessionId(sessionId);
      setCurrentSession(sess);
    }

    // Affichage optimiste du message user
    const optimistic: ChatMessage = {
      id: "tmp-" + Date.now(),
      role: "user",
      content: text,
      tool_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setSending(true);
    setError(null);

    try {
      const res = await api.chat(sessionId, text);
      setMessages((m) => [
        ...m,
        {
          id: res.message_id,
          role: "assistant",
          content: res.answer,
          tool_used: res.tools_used.join(",") || null,
          created_at: new Date().toISOString(),
        },
      ]);
      setSidebarRefresh((k) => k + 1); // pour mettre à jour le titre auto-généré
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur");
      // Retire le message optimiste en cas d'échec
      setMessages((m) => m.filter((msg) => msg.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }

  async function handleEndSession(triggerFeedback: boolean) {
    if (!currentSessionId || currentSession?.status === "ended") {
      setShowInactivity(false);
      if (triggerFeedback) setShowFeedback(true);
      return;
    }
    try {
      const res = await api.endSession(currentSessionId);
      setMessages((m) => [
        ...m,
        {
          id: "farewell-" + Date.now(),
          role: "assistant",
          content: res.farewell,
          tool_used: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setCurrentSession((s) => (s ? { ...s, status: "ended" } : s));
      setSidebarRefresh((k) => k + 1);
    } catch (err) {
      console.error(err);
    } finally {
      setShowInactivity(false);
      if (triggerFeedback) setShowFeedback(true);
    }
  }

  const isEnded = currentSession?.status === "ended";

  return (
    <div className="h-screen flex">
      <Sidebar
        currentSessionId={currentSessionId}
        onSelect={setCurrentSessionId}
        onNew={handleNew}
        refreshKey={sidebarRefresh}
      />

      <main className="flex-1 flex flex-col bg-slate-50">
        <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-slate-800">
              {currentSession?.title || "Chatbot Finance"}
            </h1>
            <p className="text-xs text-slate-500">
              Spécialisé en éducation financière (BdF, INC) + recherche web
            </p>
          </div>
          {currentSession?.status === "active" && (
            <button
              onClick={() => handleEndSession(true)}
              className="text-sm border border-slate-300 hover:bg-slate-50 px-3 py-1.5 rounded-lg"
            >
              Terminer la conversation
            </button>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && !sending && (
            <div className="h-full flex items-center justify-center text-center text-slate-400">
              <div>
                <p className="text-lg">💰 Posez-moi une question</p>
                <p className="text-sm mt-2">
                  ex : « C'est quoi un Livret A ? » ou « Taux du PEL en 2026 ? »
                </p>
              </div>
            </div>
          )}

          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}

          {sending && (
            <MessageBubble
              message={{
                role: "assistant",
                content: "",
                tool_used: null,
              }}
              pending
            />
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded my-3">
              {error}
            </p>
          )}
        </div>

        <div className="border-t border-slate-200 bg-white p-4">
          <ChatInput
            onSend={handleSend}
            disabled={sending || isEnded}
            placeholder={
              isEnded
                ? "Conversation terminée. Crée-en une nouvelle dans la sidebar."
                : undefined
            }
          />
        </div>
      </main>

      {showInactivity && (
        <InactivityModal
          onContinue={() => setShowInactivity(false)}
          onEnd={() => handleEndSession(true)}
        />
      )}

      {showFeedback && currentSessionId && (
        <FeedbackModal
          sessionId={currentSessionId}
          onClose={() => {
            setShowFeedback(false);
            setSidebarRefresh((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}
