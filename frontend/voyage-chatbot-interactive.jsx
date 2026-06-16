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
const labelForTool = (t) => {
  if (!t) return null;
  const labels = String(t).split('+').map((p) => TOOL_LABELS[p]).filter(Boolean);
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

const Msg = {
  Bot: ({ children, time, tool }) => (
    <div className="va-msg va-msg--bot va-anim-in">
      <div className="va-msg__meta">
        <span className="va-msg__avatar"><ISparkles size={13} /></span>
        <span>Assistant</span>
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
        <span>Vous</span>
      </div>
      <div className="va-msg__body">{children}</div>
    </div>
  ),
  Thinking: () => (
    <div className="va-msg va-msg--bot va-anim-in">
      <div className="va-msg__meta">
        <span className="va-msg__avatar"><ISparkles size={13} /></span>
        <span>Assistant</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span>écrit…</span>
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
          <span className="va-quick__title">{title}</span>
          <span className="va-quick__sub">{sub}</span>
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

const ChatHistorySidebar = ({ isAuth, sessions, currentToken, onLoadSession, onRequestDelete, onLogin }) => (
  <aside className="va-chatside">
    <div className="va-chatside__head">
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--va-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Historique
      </div>
    </div>
    {!isAuth ? (
      <div className="va-chatside__login">
        <p>Connectez-vous pour retrouver l&rsquo;historique de vos conversations sur tous vos appareils.</p>
        <button onClick={onLogin} type="button">Se connecter</button>
      </div>
    ) : sessions.length === 0 ? (
      <div className="va-chatside__empty">Aucune conversation pour l&rsquo;instant.</div>
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
              <span className="va-chatside__item-title">{s.title || 'Conversation'}</span>
              <span className="va-chatside__item-meta">{s.message_count} message{s.message_count > 1 ? 's' : ''}</span>
            </button>
            <button
              type="button"
              className="va-chatside__delete"
              title="Supprimer cette conversation"
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
        title={sidebarOpen ? 'Masquer l’historique' : 'Afficher l’historique'}
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
      }}>Assistant</span>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <span className="va-chat__status">En ligne · répond en 2 s</span>
      <button
        className="va-btn va-btn--sm va-btn--secondary"
        type="button"
        onClick={onEnd}
        disabled={!canEnd}
        title="Mettre fin à la conversation et noter l’assistant"
      >
        Mettre fin à la conversation
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
        aria-label={`${n} étoile${n > 1 ? 's' : ''}`}
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
        Êtes-vous toujours là&nbsp;?
      </div>
      <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
        Aucun message depuis quelques minutes. Souhaitez-vous mettre fin à cette conversation&nbsp;?
        Votre échange sera conservé et vous pourrez nous laisser une note.
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        <button className="va-btn va-btn--secondary" type="button" onClick={onStay}>
          Continuer la conversation
        </button>
        <button className="va-btn va-btn--primary" type="button" onClick={onEnd}>
          Mettre fin
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
          Comment s’est passée votre expérience&nbsp;?
        </div>
        <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 18, lineHeight: 1.5 }}>
          Votre avis nous aide à améliorer l’assistant pour les prochains voyageurs.
        </div>
        <StarRating value={rating} onChange={setRating} />
        <div style={{ fontSize: 13, color: 'var(--va-text-muted)', margin: '6px 0 14px' }}>
          {rating === 0 ? 'Sélectionnez une note' :
           rating === 5 ? 'Excellent — merci !' :
           rating === 4 ? 'Très bien' :
           rating === 3 ? 'Correct' :
           rating === 2 ? 'Peut mieux faire' :
           'Décevant'}
        </div>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Un commentaire à laisser ? (optionnel)"
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
            Passer
          </button>
          <button
            className="va-btn va-btn--primary"
            type="button"
            onClick={() => onSubmit(rating || 3, feedback)}
            disabled={submitting}
          >
            {submitting ? 'Envoi…' : 'Terminer'}
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
        Supprimer définitivement cette conversation&nbsp;?
      </div>
      <div style={{ fontSize: 14, color: 'var(--va-text-muted)', marginBottom: 22, lineHeight: 1.5 }}>
        {session && session.title ? (
          <>L’échange « <strong style={{ color: 'var(--va-text)' }}>{session.title}</strong> » sera retiré de votre historique.</>
        ) : (
          <>Cette conversation sera retirée de votre historique.</>
        )}
        <br />Cette action est irréversible.
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        <button className="va-btn va-btn--secondary" type="button" onClick={onCancel} disabled={submitting}>
          Annuler
        </button>
        <button
          className="va-btn va-btn--primary"
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          style={{ background: 'var(--va-accent)' }}
        >
          {submitting ? 'Suppression…' : 'Supprimer'}
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
  const [sidebarOpen, setSidebarOpen] = React.useState(true);
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
      setErrorMsg('Reconnaissance vocale non supportée par ce navigateur. Utilisez Chrome.');
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
        setErrorMsg(`Reconnaissance vocale : ${e.error}`);
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
            time: new Date(m.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
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
      setErrorMsg(`Impossible de joindre l’assistant (${e.message}). Le backend tourne-t-il sur ${window.VA_CONFIG.API_BASE} ?`);
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
        time: new Date(m.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
        tool: labelForTool(m.tool_used),
      })));
      setQuickReplies([]);
    } catch (e) {
      setErrorMsg(`Impossible de charger la conversation : ${e.message}`);
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
      }]);
      setQuickReplies(res.quick_replies || []);
      refreshSessions();
      speak(res.answer);
    } catch (e) {
      setErrorMsg(`Erreur : ${e.message}`);
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
      setErrorMsg(`Impossible d’enregistrer votre note : ${e.message}`);
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
              setErrorMsg(`Suppression impossible : ${e.message}`);
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
                    Bonjour{auth && auth.user ? `, ${auth.user.prenom}` : ''}, je suis l&rsquo;assistant Voyage.
                  </h1>
                  <p className="va-welcome__sub">
                    Je peux consulter vos billets, modifier vos réservations et lancer des réclamations à votre place — après une rapide vérification d&rsquo;identité. Posez-moi aussi vos questions sur les bagages, tarifs, destinations.
                  </p>
                </div>
                <QuickRepliesInt onPick={send} />
                <div className="va-privacy" style={{ alignSelf: 'center' }}>
                  <IShield size={14} className="va-privacy__icon" />
                  Vos informations restent privées. Conversations chiffrées de bout en bout.
                </div>
              </>
            ) : (
              <>
                {messages.map((m, i) => (
                  m.kind === 'user'
                    ? <Msg.User key={i} time={m.time}>{m.content}</Msg.User>
                    : <Msg.Bot key={i} time={m.time} tool={m.tool}>{renderRichText(m.content)}</Msg.Bot>
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
                placeholder="Posez votre question à l’assistant Voyage…"
                disabled={!sessionToken}
              />
              <button className="va-chat__input__btn" title="Pièce jointe" type="button"><IPaperclip size={17} /></button>
              <button
                className={`va-chat__input__btn ${speakEnabled ? 'is-active' : ''}`}
                title={speakEnabled ? 'Couper la lecture vocale' : 'Activer la lecture vocale'}
                type="button"
                onClick={() => setSpeakEnabled((v) => !v)}
                style={speakEnabled ? { color: 'var(--va-accent, #F5A623)' } : undefined}
              >
                {speakEnabled ? <IVolume size={17} /> : <IVolumeOff size={17} />}
              </button>
              <button
                className={`va-chat__input__btn ${listening ? 'is-active' : ''}`}
                title={listening ? 'Arrêter la dictée' : 'Dicter à la voix'}
                type="button"
                onClick={toggleListening}
                disabled={!sessionToken}
                style={listening ? { color: 'var(--va-accent, #F5A623)', animation: 'va-pulse 1.4s infinite' } : undefined}
              >
                <IMic size={17} />
              </button>
              <button
                className={`va-chat__input__btn va-chat__input__send ${input.trim() ? 'is-active' : ''}`}
                title="Envoyer"
                onClick={onSendInput}
                disabled={!input.trim() || thinking}
                type="button"
              >
                <IArrowUp size={17} />
              </button>
            </div>
            <div className="va-chat__hint">
              L&rsquo;assistant peut vérifier votre identité pour accéder à vos billets. Conversations chiffrées · supprimées après 30 jours.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { InteractiveChat });
