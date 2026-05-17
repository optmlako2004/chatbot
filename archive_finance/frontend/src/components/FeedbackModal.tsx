import { useState } from "react";

import { api, ApiError } from "../api/client";

interface Props {
  sessionId: string;
  onClose: (submitted: boolean) => void;
}

export default function FeedbackModal({ sessionId, onClose }: Props) {
  const [rating, setRating] = useState<number>(0);
  const [hover, setHover] = useState<number>(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (rating < 1) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.sendFeedback(sessionId, rating, comment.trim() || undefined);
      onClose(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
        <h2 className="text-xl font-bold mb-1">Heureux d'avoir pu vous aider 🙂</h2>
        <p className="text-slate-600 text-sm mb-5">
          Avant de partir, donnez-nous votre avis sur cette conversation.
        </p>

        <div className="flex justify-center gap-2 mb-4">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              onMouseEnter={() => setHover(n)}
              onMouseLeave={() => setHover(0)}
              className="text-4xl transition-transform hover:scale-110"
              aria-label={`${n} étoile${n > 1 ? "s" : ""}`}
            >
              <span
                className={
                  (hover || rating) >= n
                    ? "text-yellow-400"
                    : "text-slate-300"
                }
              >
                ★
              </span>
            </button>
          ))}
        </div>

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Un commentaire ? (optionnel)"
          rows={3}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none mb-3"
        />

        {error && (
          <p className="text-sm text-red-600 bg-red-50 p-2 rounded mb-3">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onClose(false)}
            className="flex-1 border border-slate-300 hover:bg-slate-50 font-medium py-2 rounded-lg transition"
          >
            Plus tard
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={rating < 1 || submitting}
            className="flex-1 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition"
          >
            {submitting ? "Envoi..." : "Envoyer"}
          </button>
        </div>
      </div>
    </div>
  );
}
