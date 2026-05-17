// Bouton flottant en bas à droite. Affiche un badge si conversation non lue.

interface Props {
  onClick: () => void;
  isOpen: boolean;
}

export default function ChatBubble({ onClick, isOpen }: Props) {
  return (
    <button
      onClick={onClick}
      aria-label={isOpen ? "Fermer le chatbot" : "Ouvrir le chatbot"}
      className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full bg-brand-600 hover:bg-brand-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center group"
    >
      {isOpen ? (
        // Icône X
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      ) : (
        // Icône bulle de chat
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      )}
    </button>
  );
}
