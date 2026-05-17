// Point d'entrée du widget chatbot — à importer dans n'importe quelle app React.
//
// USAGE :
//   import { ChatbotWidget } from "./widget/ChatbotWidget";
//   <App>
//     <MaPage />
//     <ChatbotWidget />
//   </App>
//
// L'auth est gérée en interne (via AuthContext) :
//   - utilise le JWT du localStorage si l'user est connecté
//   - sinon mode anonyme avec UUID en localStorage (X-Anonymous-Id)
//
// Le widget s'affiche par-dessus toute l'app via position: fixed.

import { useState } from "react";

import ChatBubble from "./ChatBubble";
import ChatPopup from "./ChatPopup";

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {isOpen && <ChatPopup onClose={() => setIsOpen(false)} />}
      <ChatBubble onClick={() => setIsOpen((o) => !o)} isOpen={isOpen} />
    </>
  );
}
