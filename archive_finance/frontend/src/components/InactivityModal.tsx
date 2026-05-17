interface Props {
  onContinue: () => void;
  onEnd: () => void;
}

export default function InactivityModal({ onContinue, onEnd }: Props) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6">
        <h2 className="text-lg font-bold mb-2">Vous êtes toujours là ?</h2>
        <p className="text-slate-600 text-sm mb-5">
          Vous semblez inactif depuis 2 minutes. Souhaitez-vous terminer cette
          conversation ?
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onContinue}
            className="flex-1 border border-slate-300 hover:bg-slate-50 font-medium py-2 rounded-lg transition"
          >
            Continuer
          </button>
          <button
            type="button"
            onClick={onEnd}
            className="flex-1 bg-slate-800 hover:bg-slate-900 text-white font-medium py-2 rounded-lg transition"
          >
            Terminer
          </button>
        </div>
      </div>
    </div>
  );
}
