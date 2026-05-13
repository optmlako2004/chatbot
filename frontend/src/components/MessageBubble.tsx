import type { ChatMessage } from "../api/types";

const TOOL_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  rag_finance: { label: "Base finance", icon: "📚", color: "bg-blue-100 text-blue-700" },
  web_search: { label: "Recherche web", icon: "🌐", color: "bg-emerald-100 text-emerald-700" },
};

interface Props {
  message: Omit<ChatMessage, "id" | "created_at"> & {
    id?: string;
    created_at?: string;
  };
  pending?: boolean;
}

export default function MessageBubble({ message, pending }: Props) {
  const isUser = message.role === "user";
  const tools = message.tool_used?.split(",").filter(Boolean) || [];

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {!isUser && tools.length > 0 && (
          <div className="flex gap-1 mb-1">
            {tools.map((t) => {
              const info = TOOL_LABELS[t.trim()];
              if (!info) return null;
              return (
                <span
                  key={t}
                  className={`text-xs px-2 py-0.5 rounded-full ${info.color}`}
                >
                  {info.icon} {info.label}
                </span>
              );
            })}
          </div>
        )}

        <div
          className={`px-4 py-3 rounded-2xl whitespace-pre-wrap leading-relaxed text-sm ${
            isUser
              ? "bg-brand-600 text-white rounded-br-sm"
              : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm"
          }`}
        >
          {pending ? (
            <span className="inline-flex gap-1">
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
            </span>
          ) : (
            message.content
          )}
        </div>
      </div>
    </div>
  );
}
