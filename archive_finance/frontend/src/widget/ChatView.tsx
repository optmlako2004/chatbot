// Vue "chat" du widget : messages d'une conversation + input.
// Gère : chargement initial, envoi message, inactivité 2 min, fin de session, feedback.

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api/client";
import type { ChatMessage, ChatSession } from "../api/types";
import ChatInput from "../components/ChatInput";
import FeedbackModal from "../components/FeedbackModal";
import InactivityModal from "../components/InactivityModal";
import MessageBubble from "../components/MessageBubble";
import { useInactivity } from "../hooks/useInactivity";

const INACTIVITY_MS = 2 * 60 * 1000;

interface Props {
  sessionId: string | null; // null = nouvelle conv (créée à l'envoi du 1er message)
  onSessionChange: (id: string) => void; // remonte le nouvel id à ChatPopup
  onSessionRefreshed: () => void; // pour rafraîchir la liste après chat
}

export default function ChatView({
  sessionId,
  onSessionChange,
  onSessionRefreshed,
}: Props) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showInactivity, setShowInactivity] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, sending]);

  // Charge la session existante (ou reset pour une nouvelle conv)
  useEffect(() => {
    setError(null);
    if (!sessionId) {
      setSession(null);
      setMessages([]);
      return;
    }
    let cancelled = false;
    Promise.all([api.getSession(sessionId), api.getMessages(sessionId)])
      .then(([sess, msgs]) => {
        if (cancelled) return;
        setSession(sess);
        setMessages(msgs);
      })
      .catch(() => !cancelled && setError("Conversation introuvable."));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const inactivityEnabled =
    session?.status === "active" && !showInactivity && !showFeedback;
  useInactivity(INACTIVITY_MS, () => setShowInactivity(true), inactivityEnabled);

  async function handleSend(text: string) {
    let sid = sessionId;
    if (!sid) {
      try {
        const sess = await api.createSession();
        sid = sess.id;
        setSession(sess);
        onSessionChange(sid);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Erreur");
        return;
      }
    }

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
      const res = await api.chat(sid, text);
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
      onSessionRefreshed();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur");
      setMessages((m) => m.filter((msg) => msg.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }

  async function handleEnd(triggerFeedback: boolean) {
    if (!sessionId || session?.status === "ended") {
      setShowInactivity(false);
      if (triggerFeedback) setShowFeedback(true);
      return;
    }
    try {
      const res = await api.endSession(sessionId);
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
      setSession((s) => (s ? { ...s, status: "ended" } : s));
      onSessionRefreshed();
    } catch (err) {
      console.error(err);
    } finally {
      setShowInactivity(false);
      if (triggerFeedback) setShowFeedback(true);
    }
  }

  const isEnded = session?.status === "ended";

  return (
    <>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 bg-slate-50">
        {messages.length === 0 && !sending && (
          <div className="h-full flex items-center justify-center text-center text-slate-400 text-sm">
            <div>
              <div className="text-4xl mb-2">👋</div>
              <p>Bonjour ! Posez-moi une question.</p>
              <p className="text-xs mt-1">
                ex : « C'est quoi un Livret A ? »
              </p>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {sending && (
          <MessageBubble
            message={{ role: "assistant", content: "", tool_used: null }}
            pending
          />
        )}

        {error && (
          <p className="text-xs text-red-600 bg-red-50 p-2 rounded my-2">{error}</p>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white p-3 space-y-2">
        <ChatInput
          onSend={handleSend}
          disabled={sending || isEnded}
          placeholder={
            isEnded
              ? "Conversation terminée."
              : "Posez votre question…"
          }
        />
        {session?.status === "active" && messages.length > 0 && (
          <button
            onClick={() => handleEnd(true)}
            className="w-full text-xs text-slate-500 hover:text-slate-700 underline"
          >
            Terminer la conversation
          </button>
        )}
      </div>

      {showInactivity && (
        <InactivityModal
          onContinue={() => setShowInactivity(false)}
          onEnd={() => handleEnd(true)}
        />
      )}

      {showFeedback && sessionId && (
        <FeedbackModal
          sessionId={sessionId}
          onClose={() => {
            setShowFeedback(false);
            onSessionRefreshed();
          }}
        />
      )}
    </>
  );
}
