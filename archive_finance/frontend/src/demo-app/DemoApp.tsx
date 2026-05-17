// FAKE app finance pour la démo. Ton coéquipier la remplacera par la vraie app.
// Le widget chatbot est ajouté ici via <ChatbotWidget />.

import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import ChatbotWidget from "../widget/ChatbotWidget";

const FAKE_TRANSACTIONS = [
  { id: 1, label: "Salaire", amount: 2400, date: "01 mai", category: "💼" },
  { id: 2, label: "Loyer", amount: -780, date: "03 mai", category: "🏠" },
  { id: 3, label: "Carrefour", amount: -82.5, date: "05 mai", category: "🛒" },
  { id: 4, label: "Spotify", amount: -9.99, date: "07 mai", category: "🎵" },
  { id: 5, label: "Restaurant", amount: -34, date: "10 mai", category: "🍽️" },
];

export default function DemoApp() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
              💰
            </div>
            <h1 className="font-bold text-slate-800">FinApp <span className="text-xs font-normal text-slate-500">(démo)</span></h1>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <a href="#" className="text-slate-700 hover:text-brand-600 font-medium">Tableau de bord</a>
            <a href="#" className="text-slate-500 hover:text-brand-600">Transactions</a>
            <a href="#" className="text-slate-500 hover:text-brand-600">Objectifs</a>
            {user && !user.is_anonymous ? (
              <span className="ml-2 px-3 py-1 rounded-full bg-slate-100 text-xs font-medium">
                {user.name || user.email}
              </span>
            ) : (
              <Link to="/login" className="ml-2 px-3 py-1 rounded-lg bg-brand-600 text-white text-xs font-medium hover:bg-brand-700">
                Se connecter
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* Bandeau d'explication (uniquement pour la soutenance) */}
      <div className="bg-amber-50 border-b border-amber-200 text-amber-900 text-sm">
        <div className="max-w-6xl mx-auto px-6 py-2 flex items-center gap-2">
          <span>ℹ️</span>
          <span>
            Ceci est une <strong>maquette</strong> pour montrer l'intégration du chatbot.
            Cliquez sur la bulle <span className="inline-block w-5 h-5 rounded-full bg-brand-600 text-white text-xs font-bold leading-5 text-center">💬</span>{" "}
            en bas à droite pour discuter avec l'assistant finance.
          </span>
        </div>
      </div>

      {/* Contenu */}
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Carte solde */}
        <div className="bg-gradient-to-br from-brand-600 to-brand-700 text-white rounded-2xl p-6 shadow-lg">
          <p className="text-sm text-brand-50/80">Solde disponible</p>
          <p className="text-4xl font-bold mt-1">3 247,50 €</p>
          <p className="text-sm text-brand-50/80 mt-2">+ 1,2 % ce mois-ci</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Stat icon="📈" label="Revenus du mois" value="2 400 €" />
          <Stat icon="📉" label="Dépenses du mois" value="906,49 €" />
          <Stat icon="💰" label="Épargne du mois" value="1 493,51 €" highlight />
        </div>

        {/* Transactions */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="font-semibold text-slate-800">Transactions récentes</h2>
          </div>
          <ul>
            {FAKE_TRANSACTIONS.map((t) => (
              <li
                key={t.id}
                className="flex items-center gap-4 px-6 py-3 border-b border-slate-100 last:border-0"
              >
                <span className="text-2xl">{t.category}</span>
                <div className="flex-1">
                  <p className="font-medium text-slate-800">{t.label}</p>
                  <p className="text-xs text-slate-500">{t.date}</p>
                </div>
                <span
                  className={`font-semibold ${
                    t.amount > 0 ? "text-emerald-600" : "text-slate-700"
                  }`}
                >
                  {t.amount > 0 ? "+" : ""}
                  {t.amount.toFixed(2)} €
                </span>
              </li>
            ))}
          </ul>
        </div>
      </main>

      {/* 👇 LE WIDGET — UNE LIGNE À AJOUTER DANS L'APP DU COÉQUIPIER */}
      <ChatbotWidget />
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  highlight,
}: {
  icon: string;
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl p-4 border ${
        highlight
          ? "bg-emerald-50 border-emerald-200"
          : "bg-white border-slate-200"
      }`}
    >
      <p className="text-2xl">{icon}</p>
      <p className="text-xs text-slate-500 mt-2">{label}</p>
      <p className="text-xl font-bold text-slate-800 mt-1">{value}</p>
    </div>
  );
}
