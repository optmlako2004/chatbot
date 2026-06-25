/* Voyage Assistant — chatbot interactif branché au backend FastAPI.
   - Sidebar gauche : historique (logué) ou CTA login
   - Hamburger toggle dans le header
   - Tool labels affichés sur les réponses bot
   - Reprise d'une conversation passée via /chat/{token}/history */

const TOOL_LABELS = {
  query_billet: 'consulte la BDD billets',
  query_trajet: 'consulte la BDD trajets',
  identity_check: 'vérifie l’identité',
  create_reclamation: 'crée la réclamation',
  rag_stub: 'documentation',
  rag: 'documentation',
  web: 'recherche web',
  web_search: 'recherche web',
  api: 'infos temps réel',
};
// "gemini" est volontairement exclu : pas besoin d'étiquette quand c'est juste l'IA qui répond.
// Les tags composés ("api+web", "rag+web") sont décomposés et joints par " + ".
const labelForTool = (toolKey) => {
  if (!toolKey) return null;
  const labels = String(toolKey).split('+').map((p) => TOOL_LABELS[p]).filter(Boolean).map((l) => t(l));
  return labels.length ? labels.join(' + ') : null;
};

/* Parse les liens Markdown [texte](url) et les URLs nues en éléments React cliquables.
   Préserve les retours à la ligne. */
const renderRichText = (text) => {
  if (!text) return null;
  const linkRe = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s)]+)/g;
  const lines = String(text).split('\n');
  return lines.map((line, lineIdx) => {
    const parts = [];
    let last = 0;
    let m;
    linkRe.lastIndex = 0;
    while ((m = linkRe.exec(line)) !== null) {
      if (m.index > last) parts.push(line.slice(last, m.index));
      const url = m[2] || m[3];
      const label = m[1] || url.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      parts.push(
        <a
          key={`l-${lineIdx}-${m.index}`}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--va-accent)', textDecoration: 'underline', textUnderlineOffset: 2 }}
        >
          {label}
        </a>
      );
      last = m.index + m[0].length;
    }
    if (last < line.length) parts.push(line.slice(last));
    return (
      <React.Fragment key={lineIdx}>
        {parts}
        {lineIdx < lines.length - 1 && <br />}
      </React.Fragment>
    );
  });
};

const QUICK_ITEMS = [
  { id: 'problem', Icon: IAlert, title: 'Problème avec mon voyage',  sub: 'Retard, annulation, info trafic' },
  { id: 'modify',  Icon: IEdit,  title: 'Modifier ma réservation',   sub: 'Date, nom, point relais' },
  { id: 'claim',   Icon: IFile,  title: 'Faire une réclamation',     sub: 'Bagage, service, remboursement' },
  { id: 'help',    Icon: IHelp,  title: 'Question générale',         sub: 'Tarifs, conditions, destinations' },
];
// Le titre est envoyé au backend comme message ; on traduit uniquement l'affichage.

const Msg = {
  Bot: ({ children, time, tool }) => (
    <div className="va-msg va-msg--bot va-anim-in">
      <div className="va-msg__meta">
        <span className="va-msg__avatar"><ISparkles size={13} /></span>
        <span>{t('Assistant')}</span>
        {tool && <><span style={{ opacity: 0.5 }}>·</span><span style={{ color: 'var(--va-accent)' }}>{tool}</span></>}
        {time && <><span style={{ opacity: 0.5 }}>·</span><span>{time}</span></>}
      </div>
      <div className="va-msg__body">{children}</div>
    </div>
  ),
  User: ({ children, time }) => (
    <div className="va-msg va-msg--user va-anim-in">
      <div className="va-msg__meta">
        {time && <><span>{time}</span><span style={{ opacity: 0.5 }}>·</span></>}
        <span>{t('Vous')}</span>
      </div>
      <div className="va-msg__body">{children}</div>
    </div>
  ),
  Thinking: () => (
    <div className="va-msg va-msg--bot va-anim-in">
      <div className="va-msg__meta">
        <span className="va-msg__avatar"><ISparkles size={13} /></span>
        <span>{t('Assistant')}</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span>{t('écrit…')}</span>
      </div>
      <div className="va-msg__body">
        <div className="va-thinking"><span></span><span></span><span></span></div>
      </div>
    </div>
  ),
};

const QuickRepliesInt = ({ onPick }) => (
  <div className="va-quickgrid">
    {QUICK_ITEMS.map(({ id, Icon, title, sub }) => (
      <button key={id} className="va-quick" onClick={() => onPick(title)}>
        <span className="va-quick__icon"><Icon size={18} /></span>
        <span className="va-quick__text">
          <span className="va-quick__title">{t(title)}</span>
          <span className="va-quick__sub">{t(sub)}</span>
        </span>
        <IChevronRight size={16} className="va-quick__chev" />
      </button>
    ))}
  </div>
);

const ChipReplies = ({ items, onPick }) => (
  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
    {items.map((label, i) => (
      <button key={i} className="va-chip" style={{ height: 36, padding: '0 16px' }} onClick={() => onPick(label)}>
        {label}
      </button>
    ))}
  </div>
);

/* Cartes de résultats de recherche affichées sous une réponse bot.
   Chips de filtre transport (client-side) + cartes compactes cliquables → page réservation. */
const RESULT_FILTERS = [
  { key: 'all',    label: 'Tous',   type: null },
  { key: 'train',  label: 'Train',  type: 'train' },
  { key: 'avion',  label: 'Avion',  type: 'avion' },
  { key: 'bus',    label: 'Bus',    type: 'bus' },
  { key: 'bateau', label: 'Bateau', type: 'bateau' },
];

const ResultCards = ({ results, onSelect }) => {
  const [filter, setFilter] = React.useState('all');
  const active = RESULT_FILTERS.find((f) => f.key === filter) || RESULT_FILTERS[0];
  const shown = active.type ? results.filter((it) => it.type === active.type) : results;
  const fmtDur = (it) => {
    const dep = new Date(it.date_depart);
    const arr = new Date(it.date_arrivee);
    const mins = Math.round((arr - dep) / 60000);
    if (isNaN(mins) || mins < 0) return '';
    return `${Math.floor(mins / 60)} h ${String(mins % 60).padStart(2, '0')}`;
  };
  const fmtTime = (s) => {
    const d = new Date(s);
    return isNaN(d) ? '' : d.toLocaleTimeString(window.VA_I18N.locale(), { hour: '2-digit', minute: '2-digit' });
  };
  const fmtDate = (s) => {
    const d = new Date(s);
    return isNaN(d) ? '' : d.toLocaleDateString(window.VA_I18N.locale(), { weekday: 'short', day: 'numeric', month: 'short' });
  };
  const modeLabel = { train: 'Train', avion: 'Avion', bus: 'Bus', bateau: 'Bateau' };
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        {RESULT_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`va-chip ${filter === f.key ? 'is-active' : ''}`}
            style={{
              height: 32, padding: '0 14px',
              ...(filter === f.key ? { background: 'var(--va-accent)', color: '#fff', borderColor: 'var(--va-accent)' } : {}),
            }}
            onClick={() => setFilter(f.key)}
          >
            {t(f.label)}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {shown.length === 0 ? (
          <div style={{ fontSize: 13, color: 'var(--va-text-muted)' }}>{t('Aucun résultat pour ce filtre.')}</div>
        ) : shown.map((it) => (
          <button
            key={it.id}
            type="button"
            onClick={() => onSelect(it)}
            style={{
              textAlign: 'left', cursor: 'pointer',
              background: 'var(--va-surface)', border: '1px solid var(--va-border)',
              borderRadius: 12, padding: '12px 14px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
              transition: 'border-color 120ms ease, box-shadow 120ms ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--va-accent)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--va-border)'; }}
          >
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--va-text)', display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span>{it.compagnie}</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--va-text-muted)' }}>{t(modeLabel[it.type] || 'Train')}</span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--va-text)', marginTop: 2 }}>
                {it.depart} → {it.arrivee}
              </div>
              <div style={{ fontSize: 12, color: 'var(--va-text-muted)', marginTop: 2 }}>
                {fmtDate(it.date_depart)} · {fmtTime(it.date_depart)} · {fmtDur(it)}
              </div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--va-text)' }}>{Math.round(it.prix)} €</div>
              <div style={{ fontSize: 12, color: 'var(--va-accent)', fontWeight: 600, marginTop: 2 }}>{t('Réserver')}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

const ChatHistorySidebar = ({ isAuth, sessions, currentToken, onLoadSession, onRequestDelete, onLogin }) => (
  <aside className="va-chatside">
    <div className="va-chatside__head">
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--va-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {t('Historique')}
      </div>
    </div>
    {!isAuth ? (
      <div className="va-chatside__login">
        <p>{t('Connectez-vous pour retrouver l’historique de vos conversations sur tous vos appareils.')}</p>
        <button onClick={onLogin} type="button">{t('Se connecter')}</button>
      </div>
    ) : sessions.length === 0 ? (
      <div className="va-chatside__empty">{t('Aucune conversation pour l’instant.')}</div>
    ) : (
      <div className="va-chatside__list">
        {sessions.map((s) => (
          <div
            key={s.session_token}
            className={`va-chatside__item-wrap ${s.session_token === currentToken ? 'is-active' : ''}`}
          >
            <button
              type="button"
              className="va-chatside__item"
              onClick={() => onLoadSession(s.session_token)}
            >
              <span className="va-chatside__item-title">{s.title || t('Conversation')}</span>
              <span className="va-chatside__item-meta">{s.message_count > 1 ? t('{count} messages', { count: s.message_count }) : t('{count} message', { count: s.message_count })}</span>
            </button>
            <button
              type="button"
              className="va-chatside__delete"
              title={t('Supprimer cette conversation')}
              onClick={(e) => { e.stopPropagation(); onRequestDelete(s); }}
            >
              <ITrash size={14} />
            </button>
          </div>
        ))}
      </div>
    )}
  </aside>
);

const ChatHeadInt = ({ onEnd, onToggleSidebar, sidebarOpen, canEnd }) => (
  <header className="va-chat__head">
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <button
        className="va-iconbtn"
        title={sidebarOpen ? t('Masquer l’historique') : t('Afficher l’historique')}
        onClick={onToggleSidebar}
        type="button"
      >
        <IMenu size={18} />
      </button>
      <Wordmark size="sm" />
      <span style={{
        fontSize: 12, fontWeight: 500, color: 'var(--va-text-muted)',
        background: 'var(--va-surface-2)', border: '1px solid var(--va-border)',
        padding: '3px 9px', borderRadius: 999,
      }}>{t('Assistant')}</span>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <span className="va-chat__status">{t('En ligne · répond en 2 s')}</span>
      <button
        className="va-btn va-btn--sm va-btn--secondary"
        type="button"
        onClick={onEnd}
        disabled={!canEnd}
        title={t('Mettre fin à la conversation et noter l’assistant')}
      >
        {t('Mettre fin à la conversation')}
      </button>
    </div>
  </header>
);

/* Composant : étoiles cliquables (1 à 5) */
const StarRating = ({ value, onChange }) => (
  <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
    {[1, 2, 3, 4, 5].map((n) => (
      <button
        key={n}
        type="button"
        onClick={() => onChange(n)}
        aria-label={n > 1 ? t('{n} étoiles', { n }) : t('{n} étoile', { n })}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          padding: 4, fontSize: 32, lineHeight: 1,
          color: n <= value ? 'var(--va-accent)' : 'var(--va-border)',
          transition: 'color 120ms ease',
        }}
      >
        ★
      </button>
    ))}
  </div>
);

/* Modale d'inactivité — propose de continuer ou de mettre fin */
const InactivityModal = ({ onStay, onEnd }) => (
  <div
    role="dialog"
    aria-modal="true"
    style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}
  >
    <div style={{
      background: 'var(--va-surface)', border: '1px solid var(--va-border)',
      borderRadius: 16, padding: 28, maxWidth: 460, width: '100%',
      boxShadow: '0 24px 60px rgba(0,0,0,0.25)', textAlign: 'center',
    }}>
      <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--va-text)', marginBottom: 8 }}>
        {t('Êtes-vous toujours là ?')}
      </div>
      <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
        {t('Aucun message depuis quelques minutes. Souhaitez-vous mettre fin à cette conversation ? Votre échange sera conservé et vous pourrez nous laisser une note.')}
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        <button className="va-btn va-btn--secondary" type="button" onClick={onStay}>
          {t('Continuer la conversation')}
        </button>
        <button className="va-btn va-btn--primary" type="button" onClick={onEnd}>
          {t('Mettre fin')}
        </button>
      </div>
    </div>
  </div>
);

/* Modale de fin — étoiles + commentaire */
const RatingModal = ({ onSubmit, onClose, submitting }) => {
  const [rating, setRating] = React.useState(0);
  const [feedback, setFeedback] = React.useState('');
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed', inset: 0, zIndex: 1001,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      }}
    >
      <div style={{
        background: 'var(--va-surface)', border: '1px solid var(--va-border)',
        borderRadius: 16, padding: 28, maxWidth: 480, width: '100%',
        boxShadow: '0 24px 60px rgba(0,0,0,0.25)', textAlign: 'center',
      }}>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--va-text)', marginBottom: 8 }}>
          {t('Comment s’est passée votre expérience ?')}
        </div>
        <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 18, lineHeight: 1.5 }}>
          {t('Votre avis nous aide à améliorer l’assistant pour les prochains voyageurs.')}
        </div>
        <StarRating value={rating} onChange={setRating} />
        <div style={{ fontSize: 13, color: 'var(--va-text-muted)', margin: '6px 0 14px' }}>
          {rating === 0 ? t('Sélectionnez une note') :
           rating === 5 ? t('Excellent — merci !') :
           rating === 4 ? t('Très bien') :
           rating === 3 ? t('Correct') :
           rating === 2 ? t('Peut mieux faire') :
           t('Décevant')}
        </div>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder={t('Un commentaire à laisser ? (optionnel)')}
          rows={3}
          style={{
            width: '100%', resize: 'vertical', padding: '10px 12px',
            border: '1px solid var(--va-border)', borderRadius: 10,
            fontFamily: 'inherit', fontSize: 14, color: 'var(--va-text)',
            background: 'var(--va-bg)', marginBottom: 16,
          }}
        />
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="va-btn va-btn--secondary" type="button" onClick={onClose} disabled={submitting}>
            {t('Passer')}
          </button>
          <button
            className="va-btn va-btn--primary"
            type="button"
            onClick={() => onSubmit(rating || 3, feedback)}
            disabled={submitting}
          >
            {submitting ? t('Envoi…') : t('Terminer')}
          </button>
        </div>
      </div>
    </div>
  );
};

/* Modale de confirmation de suppression d'une conversation */
const ConfirmDeleteModal = ({ session, onConfirm, onCancel, submitting }) => (
  <div
    role="dialog"
    aria-modal="true"
    style={{
      position: 'fixed', inset: 0, zIndex: 1002,
      background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}
    onClick={(e) => { if (e.target === e.currentTarget && !submitting) onCancel(); }}
  >
    <div style={{
      background: 'var(--va-surface)', border: '1px solid var(--va-border)',
      borderRadius: 16, padding: 28, maxWidth: 460, width: '100%',
      boxShadow: '0 24px 60px rgba(0,0,0,0.25)', textAlign: 'center',
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: '50%',
        background: 'rgba(217, 119, 87, 0.12)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 16, color: 'var(--va-accent)',
      }}>
        <ITrash size={26} />
      </div>
      <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--va-text)', marginBottom: 8 }}>
        {t('Supprimer définitivement cette conversation ?')}
      </div>
      <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 22, lineHeight: 1.5 }}>
        {session && session.title ? (
          <>{t('L’échange')} « <strong style={{ color: 'var(--va-text)' }}>{session.title}</strong> » {t('sera retiré de votre historique.')}</>
        ) : (
          <>{t('Cette conversation sera retirée de votre historique.')}</>
        )}
        <br />{t('Cette action est irréversible.')}
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        <button className="va-btn va-btn--secondary" type="button" onClick={onCancel} disabled={submitting}>
          {t('Annuler')}
        </button>
        <button
          className="va-btn va-btn--primary"
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          style={{ background: 'var(--va-accent)' }}
        >
          {submitting ? t('Suppression…') : t('Supprimer')}
        </button>
      </div>
    </div>
  </div>
);

const VA_CHAT_LS_KEY = 'va_chat_session_token';

const InteractiveChat = ({ go, ctx, auth, onRequestLogin }) => {
  const [sessionToken, setSessionToken] = React.useState(null);
  const [messages, setMessages] = React.useState([]);
  const [quickReplies, setQuickReplies] = React.useState([]);
  const [input, setInput] = React.useState('');
  const [thinking, setThinking] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState(null);
  const [sessions, setSessions] = React.useState([]);
  // Sidebar fermée par défaut sur mobile : sinon la colonne 280px écrase le chat
  // (la zone de saisie passait hors écran → impression que « le chatbot ne réagit plus »).
  const [sidebarOpen, setSidebarOpen] = React.useState(
    () => typeof window === 'undefined' || window.innerWidth > 860
  );
  const [showInactivity, setShowInactivity] = React.useState(false);
  const [showRating, setShowRating] = React.useState(false);
  const [submittingRating, setSubmittingRating] = React.useState(false);
  const [pendingDelete, setPendingDelete] = React.useState(null);
  const [deletingSession, setDeletingSession] = React.useState(false);
  const [listening, setListening] = React.useState(false);
  const [speakEnabled, setSpeakEnabled] = React.useState(() => {
    try { return localStorage.getItem('va.speak') === '1'; } catch { return false; }
  });
  const scrollRef = React.useRef(null);
  const inactivityRef = React.useRef(null);
  const recognitionRef = React.useRef(null);
  const fileInputRef = React.useRef(null);

  // Synthèse vocale d'un texte (lit à voix haute la dernière réponse bot)
  const speak = React.useCallback((text) => {
    if (!speakEnabled || !window.speechSynthesis || !text) return;
    try {
      window.speechSynthesis.cancel();
      const cleaned = String(text).replace(/\*\*/g, '').replace(/`/g, '').slice(0, 500);
      const u = new SpeechSynthesisUtterance(cleaned);
      u.lang = 'fr-FR';
      u.rate = 1.0;
      u.pitch = 1.0;
      window.speechSynthesis.speak(u);
    } catch {}
  }, [speakEnabled]);

  React.useEffect(() => {
    try { localStorage.setItem('va.speak', speakEnabled ? '1' : '0'); } catch {}
    if (!speakEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
  }, [speakEnabled]);

  // Démarre/arrête la reconnaissance vocale (Web Speech API)
  const toggleListening = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setErrorMsg(t('Reconnaissance vocale non supportée par ce navigateur. Utilisez Chrome.'));
      return;
    }
    if (listening && recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      return;
    }
    const rec = new SR();
    rec.lang = 'fr-FR';
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => setListening(true);
    rec.onresult = (e) => {
      let interim = '';
      let final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) final += r[0].transcript;
        else interim += r[0].transcript;
      }
      setInput(final || interim);
    };
    rec.onerror = (e) => {
      setListening(false);
      if (e.error !== 'no-speech' && e.error !== 'aborted') {
        setErrorMsg(t('Reconnaissance vocale : {error}', { error: e.error }));
      }
    };
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    try { rec.start(); } catch (err) { setListening(false); }
  };

  const now = () => {
    const d = new Date();
    return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  };

  React.useEffect(() => {
    if (scrollRef.current && messages.length > 0) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking]);

  const refreshSessions = React.useCallback(async () => {
    if (!auth || !auth.isAuth) { setSessions([]); return; }
    try {
      const list = await window.VA_API.chatSessions();
      setSessions(list || []);
    } catch { setSessions([]); }
  }, [auth && auth.isAuth]);

  const startSession = React.useCallback(async (forceNew = false) => {
    setErrorMsg(null);
    try {
      // Reprise : on tente d'abord de rouvrir la session sauvegardée localement
      let existing = null;
      if (!forceNew) {
        try { existing = localStorage.getItem(VA_CHAT_LS_KEY); } catch { /* ignore */ }
      }
      if (existing) {
        try {
          const hist = await window.VA_API.chatHistory(existing);
          setSessionToken(existing);
          setMessages(hist.map((m) => ({
            kind: m.role === 'user' ? 'user' : 'bot',
            content: m.content,
            time: new Date(m.created_at).toLocaleTimeString(window.VA_I18N.locale(), { hour: '2-digit', minute: '2-digit' }),
            tool: labelForTool(m.tool_used),
          })));
          setQuickReplies([]);
          refreshSessions();
          return;
        } catch {
          // session expirée / supprimée côté serveur : on en crée une neuve
          try { localStorage.removeItem(VA_CHAT_LS_KEY); } catch {}
        }
      }
      const res = await window.VA_API.chatStart();
      setSessionToken(res.session_token);
      try { localStorage.setItem(VA_CHAT_LS_KEY, res.session_token); } catch {}
      setMessages([]);
      setQuickReplies(res.quick_replies || []);
      refreshSessions();
    } catch (e) {
      setErrorMsg(t('Impossible de joindre l’assistant ({error}). Le backend tourne-t-il sur {url} ?', { error: e.message, url: window.VA_CONFIG.API_BASE }));
    }
  }, [refreshSessions]);

  React.useEffect(() => { startSession(); }, [startSession]);
  React.useEffect(() => { refreshSessions(); }, [refreshSessions]);

  // Quand l'utilisateur se connecte : on relie la session anonyme courante à son compte,
  // puis on rafraîchit l'historique pour qu'elle apparaisse.
  const prevIsAuth = React.useRef(false);
  React.useEffect(() => {
    const nowAuth = !!(auth && auth.isAuth);
    if (nowAuth && !prevIsAuth.current && sessionToken) {
      window.VA_API.chatStart(sessionToken).catch(() => {}).finally(() => refreshSessions());
    }
    prevIsAuth.current = nowAuth;
  }, [auth && auth.isAuth, sessionToken]);

  // Timer d'inactivité : 2 minutes après le dernier message → modale "êtes-vous toujours là ?"
  const resetInactivity = React.useCallback(() => {
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    if (showInactivity || showRating) return;
    inactivityRef.current = setTimeout(() => setShowInactivity(true), 2 * 60 * 1000);
  }, [showInactivity, showRating]);

  React.useEffect(() => {
    if (messages.length === 0) return;
    resetInactivity();
    return () => { if (inactivityRef.current) clearTimeout(inactivityRef.current); };
  }, [messages, resetInactivity]);

  const loadSession = async (tok) => {
    if (tok === sessionToken) return;
    try {
      const hist = await window.VA_API.chatHistory(tok);
      setSessionToken(tok);
      try { localStorage.setItem(VA_CHAT_LS_KEY, tok); } catch {}
      setMessages(hist.map((m) => ({
        kind: m.role === 'user' ? 'user' : 'bot',
        content: m.content,
        time: new Date(m.created_at).toLocaleTimeString(window.VA_I18N.locale(), { hour: '2-digit', minute: '2-digit' }),
        tool: labelForTool(m.tool_used),
      })));
      setQuickReplies([]);
    } catch (e) {
      setErrorMsg(t('Impossible de charger la conversation : {error}', { error: e.message }));
    }
  };

  const send = async (text) => {
    if (!sessionToken || !text.trim()) return;
    const userText = text.trim();
    setMessages((m) => [...m, { kind: 'user', content: userText, time: now() }]);
    setQuickReplies([]);
    setThinking(true);
    try {
      const res = await window.VA_API.chatMessage(sessionToken, userText);
      const tool = (res.tools_used && res.tools_used[0]) || null;
      setMessages((m) => [...m, {
        kind: 'bot', content: res.answer, time: now(),
        tool: labelForTool(tool),
        results: Array.isArray(res.results) ? res.results : null,
      }]);
      setQuickReplies(res.quick_replies || []);
      refreshSessions();
      speak(res.answer);
    } catch (e) {
      setErrorMsg(t('Erreur : {error}', { error: e.message }));
    } finally {
      setThinking(false);
    }
  };

  const onSendInput = () => {
    const txt = input.trim();
    if (!txt) return;
    setInput('');
    send(txt);
  };

  // Ouvre la page de réservation pour un trajet (depuis une carte de résultat dans le chat).
  // Construit la route object via window.enrichTrajet (même mapping que ResultsPage).
  const openTrajet = (item) => {
    if (!go) return;
    const route = window.enrichTrajet ? window.enrichTrajet(item) : item;
    go('booking', { route, pax: { adultes: 1, enfants: 0, bebes: 0 }, classId: null });
  };

  // Clic sur le trombone → ouvre le sélecteur de fichier PDF
  const onPickFile = async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ''; // permet de re-sélectionner le même fichier
    if (!file || !sessionToken) return;
    setMessages((m) => [...m, { kind: 'user', content: `📎 ${file.name}`, time: now() }]);
    setThinking(true);
    try {
      const res = await window.VA_API.extractBillet(file);
      setThinking(false);
      if (res && res.found && res.numero_billet) {
        send(t('Voici mon billet : {num}', { num: res.numero_billet }));
      } else {
        setMessages((m) => [...m, {
          kind: 'bot', time: now(),
          content: t('Ce PDF ne semble pas être un billet Voyage Assistant. Vérifiez que c’est bien le PDF reçu par e-mail.'),
        }]);
      }
    } catch (err) {
      setThinking(false);
      setErrorMsg(t('Impossible de lire ce billet : {error}', { error: err.message }));
    }
  };

  const reset = (forceNew = true) => {
    setMessages([]);
    setQuickReplies([]);
    setInput('');
    setSessionToken(null);
    try { localStorage.removeItem(VA_CHAT_LS_KEY); } catch {}
    startSession(forceNew);
  };

  const submitRating = async (rating, feedback) => {
    if (!sessionToken) { setShowRating(false); reset(); return; }
    setSubmittingRating(true);
    try {
      await window.VA_API.endSession(sessionToken, rating, feedback);
    } catch (e) {
      setErrorMsg(t('Impossible d’enregistrer votre note : {error}', { error: e.message }));
    } finally {
      setSubmittingRating(false);
      setShowRating(false);
      setShowInactivity(false);
      reset();
    }
  };

  const isInitial = messages.length === 0;
  const canEnd = !!sessionToken && messages.length > 0;

  return (
    <div className={`va-chat ${sidebarOpen ? 'va-chat--with-sidebar' : ''}`}>
      {sidebarOpen && (
        <div className="va-chatside-scrim" onClick={() => setSidebarOpen(false)} />
      )}
      {sidebarOpen && (
        <ChatHistorySidebar
          isAuth={!!(auth && auth.isAuth)}
          sessions={sessions}
          currentToken={sessionToken}
          onLoadSession={loadSession}
          onRequestDelete={(s) => setPendingDelete(s)}
          onLogin={() => onRequestLogin && onRequestLogin('login')}
        />
      )}
      {showInactivity && (
        <InactivityModal
          onStay={() => { setShowInactivity(false); resetInactivity(); }}
          onEnd={() => { setShowInactivity(false); setShowRating(true); }}
        />
      )}
      {showRating && (
        <RatingModal
          submitting={submittingRating}
          onSubmit={submitRating}
          onClose={() => { if (!submittingRating) { setShowRating(false); setShowInactivity(false); } }}
        />
      )}
      {pendingDelete && (
        <ConfirmDeleteModal
          session={pendingDelete}
          submitting={deletingSession}
          onCancel={() => setPendingDelete(null)}
          onConfirm={async () => {
            setDeletingSession(true);
            try {
              await window.VA_API.deleteSession(pendingDelete.session_token);
              if (pendingDelete.session_token === sessionToken) reset();
              refreshSessions();
              setPendingDelete(null);
            } catch (e) {
              setErrorMsg(t('Suppression impossible : {error}', { error: e.message }));
            } finally {
              setDeletingSession(false);
            }
          }}
        />
      )}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <ChatHeadInt
          onEnd={() => setShowRating(true)}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          sidebarOpen={sidebarOpen}
          canEnd={canEnd}
        />
        <div className="va-chat__scroll" ref={scrollRef} style={{ overflowY: 'auto' }}>
          <div className="va-chat__inner">
            {errorMsg && (
              <div style={{
                padding: '14px 18px', borderRadius: 'var(--va-radius-md)',
                background: 'rgba(217, 119, 87, 0.08)', border: '1px solid var(--va-accent)',
                color: 'var(--va-text)', marginBottom: 16, fontSize: 14,
              }}>
                {errorMsg}
              </div>
            )}

            {isInitial ? (
              <>
                <div className="va-welcome">
                  <div className="va-welcome__mark"><ISparkles size={22} /></div>
                  <h1 className="va-welcome__title">
                    {auth && auth.user
                      ? t('Bonjour, {name}, je suis l’assistant Voyage.', { name: auth.user.prenom })
                      : t('Bonjour, je suis l’assistant Voyage.')}
                  </h1>
                  <p className="va-welcome__sub">
                    {t('Je peux consulter vos billets, modifier vos réservations et lancer des réclamations à votre place — après une rapide vérification d’identité. Posez-moi aussi vos questions sur les bagages, tarifs, destinations.')}
                  </p>
                </div>
                <QuickRepliesInt onPick={send} />
                <div className="va-privacy" style={{ alignSelf: 'center' }}>
                  <IShield size={14} className="va-privacy__icon" />
                  {t('Vos informations restent privées. Connexion chiffrée (HTTPS).')}
                </div>
              </>
            ) : (
              <>
                {messages.map((m, i) => (
                  m.kind === 'user'
                    ? <Msg.User key={i} time={m.time}>{m.content}</Msg.User>
                    : (
                      <Msg.Bot key={i} time={m.time} tool={m.tool}>
                        {renderRichText(m.content)}
                        {m.results && m.results.length > 0 && (
                          <ResultCards results={m.results} onSelect={openTrajet} />
                        )}
                      </Msg.Bot>
                    )
                ))}
                {thinking && <Msg.Thinking />}
                {!thinking && quickReplies.length > 0 && (
                  <ChipReplies items={quickReplies} onPick={send} />
                )}
              </>
            )}
          </div>
        </div>
        <div className="va-chat__inputzone">
          <div className="va-chat__inputwrap">
            <div className="va-chat__input">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSendInput(); } }}
                placeholder={t('Posez votre question à l’assistant Voyage…')}
                disabled={!sessionToken}
              />
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                style={{ display: 'none' }}
                onChange={onPickFile}
              />
              <button
                className="va-chat__input__btn"
                title={t('Importer un billet')}
                type="button"
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                disabled={!sessionToken}
              ><IPaperclip size={17} /></button>
              <button
                className={`va-chat__input__btn ${speakEnabled ? 'is-active' : ''}`}
                title={speakEnabled ? t('Couper la lecture vocale') : t('Activer la lecture vocale')}
                type="button"
                onClick={() => setSpeakEnabled((v) => !v)}
                style={speakEnabled ? { color: 'var(--va-accent, #F5A623)' } : undefined}
              >
                {speakEnabled ? <IVolume size={17} /> : <IVolumeOff size={17} />}
              </button>
              <button
                className={`va-chat__input__btn ${listening ? 'is-active' : ''}`}
                title={listening ? t('Arrêter la dictée') : t('Dicter à la voix')}
                type="button"
                onClick={toggleListening}
                disabled={!sessionToken}
                style={listening ? { color: 'var(--va-accent, #F5A623)', animation: 'va-pulse 1.4s infinite' } : undefined}
              >
                <IMic size={17} />
              </button>
              <button
                className={`va-chat__input__btn va-chat__input__send ${input.trim() ? 'is-active' : ''}`}
                title={t('Envoyer')}
                onClick={onSendInput}
                disabled={!input.trim() || thinking}
                type="button"
              >
                <IArrowUp size={17} />
              </button>
            </div>
            <div className="va-chat__hint">
              {t('L’assistant vérifie votre identité avant tout accès à vos billets. Connexion chiffrée (HTTPS).')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { InteractiveChat });
