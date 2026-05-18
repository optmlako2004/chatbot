/* Voyage Assistant — Auth modal + hook + state.
   - useAuth() : { user, token, login, signup, googleSignIn, logout, isAuth }
   - AuthModal : modale 2 onglets (Connexion / Inscription) + bouton Google
   Persistance via localStorage. */

const AUTH_STORAGE = { TOKEN: 'va.token', USER: 'va.user' };

const useAuth = () => {
  const [token, setToken] = React.useState(() => {
    try { return localStorage.getItem(AUTH_STORAGE.TOKEN); } catch { return null; }
  });
  const [user, setUser] = React.useState(() => {
    try { return JSON.parse(localStorage.getItem(AUTH_STORAGE.USER) || 'null'); } catch { return null; }
  });

  const _persist = (tok, u) => {
    try {
      if (tok) localStorage.setItem(AUTH_STORAGE.TOKEN, tok); else localStorage.removeItem(AUTH_STORAGE.TOKEN);
      if (u) localStorage.setItem(AUTH_STORAGE.USER, JSON.stringify(u)); else localStorage.removeItem(AUTH_STORAGE.USER);
    } catch {}
    setToken(tok); setUser(u);
  };

  const login = async (email, password) => {
    const r = await window.VA_API.login(email, password);
    _persist(r.token, r.user);
    return r.user;
  };

  const signup = async (payload) => {
    const r = await window.VA_API.signup(payload);
    _persist(r.token, r.user);
    return r.user;
  };

  const googleSignIn = async () => {
    return new Promise((resolve, reject) => {
      const clientId = window.VA_CONFIG && window.VA_CONFIG.GOOGLE_CLIENT_ID;
      if (!clientId || !window.google || !window.google.accounts) {
        // Fallback stub si SDK Google non chargé ou client_id manquant
        const email = (prompt('SDK Google indisponible — entrez votre email :') || '').trim();
        if (!email) return resolve(null);
        const name = email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        window.VA_API.googleAuth({
          google_sub: 'stub-' + btoa(email).slice(0, 24),
          email, name,
          given_name: name.split(' ')[0] || 'User',
          family_name: name.split(' ').slice(1).join(' ') || 'Google',
          picture: '',
        }).then(r => { _persist(r.token, r.user); resolve(r.user); }).catch(reject);
        return;
      }

      // Flow OAuth2 popup (évite FedCM qui peut être bloqué par le navigateur)
      if (!window.google.accounts.oauth2) {
        reject(new Error('Google OAuth2 SDK indisponible'));
        return;
      }
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: 'openid email profile',
        callback: async (resp) => {
          if (resp.error) { reject(new Error(resp.error)); return; }
          try {
            const ui = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
              headers: { Authorization: `Bearer ${resp.access_token}` },
            }).then(r => r.json());
            const r = await window.VA_API.googleAuth({
              google_sub: ui.sub,
              email: ui.email,
              name: ui.name || `${ui.given_name || ''} ${ui.family_name || ''}`.trim(),
              given_name: ui.given_name || '',
              family_name: ui.family_name || '',
              picture: ui.picture || '',
            });
            _persist(r.token, r.user);
            resolve(r.user);
          } catch (err) {
            reject(err);
          }
        },
      });
      tokenClient.requestAccessToken();
    });
  };

  const logout = () => _persist(null, null);

  return { user, token, isAuth: !!token, login, signup, googleSignIn, logout };
};

const AuthModal = ({ open, onClose, defaultTab = 'login', onSuccess }) => {
  const auth = window.VA_AUTH;
  const [tab, setTab] = React.useState(defaultTab);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => { setTab(defaultTab); setError(null); }, [defaultTab, open]);
  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    const form = e.target;
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      let user;
      if (tab === 'login') {
        user = await auth.login(data.email, data.password);
      } else {
        user = await auth.signup({
          nom: data.nom, prenom: data.prenom,
          date_naissance: data.date_naissance,
          email: data.email, password: data.password,
        });
      }
      onSuccess && onSuccess(user);
      onClose && onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const doGoogle = async () => {
    setBusy(true); setError(null);
    try {
      const u = await auth.googleSignIn();
      if (u) { onSuccess && onSuccess(u); onClose && onClose(); }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="va-modal-overlay" onClick={(e) => { if (e.target.classList.contains('va-modal-overlay')) onClose(); }}>
      <div className="va-modal">
        <button className="va-modal__close" onClick={onClose} aria-label="Fermer"><IClose size={18} /></button>
        <div style={{ marginBottom: 24 }}>
          <Wordmark size="md" />
        </div>
        <h2 className="va-modal__title">{tab === 'login' ? 'Bon retour' : 'Créer un compte'}</h2>
        <p className="va-modal__sub">
          {tab === 'login' ? 'Connectez-vous pour réserver et retrouver vos conversations.' : 'Quelques infos suffisent. Vous pourrez réserver immédiatement.'}
        </p>

        <button className="va-google-btn" onClick={doGoogle} disabled={busy}>
          <span className="va-google-btn__icon">
            <svg viewBox="0 0 18 18" width="18" height="18">
              <path d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.71v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.61z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.93v2.34A9 9 0 0 0 9 18z" fill="#34A853"/>
              <path d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.17.29-1.7V4.96H.93A9 9 0 0 0 0 9c0 1.45.35 2.82.93 4.04l3.02-2.34z" fill="#FBBC05"/>
              <path d="M9 3.58c1.32 0 2.51.46 3.45 1.35l2.58-2.59C13.46.89 11.43 0 9 0 5.48 0 2.44 2.02.93 4.96L3.95 7.3C4.66 5.17 6.65 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
          </span>
          Continuer avec Google
        </button>

        <div className="va-modal__sep"><span>ou</span></div>

        <form onSubmit={submit} className="va-form">
          {tab === 'signup' && (
            <>
              <div className="va-form__row">
                <label className="va-form__field">
                  <span>Prénom</span>
                  <input name="prenom" required maxLength={100} />
                </label>
                <label className="va-form__field">
                  <span>Nom</span>
                  <input name="nom" required maxLength={100} />
                </label>
              </div>
              <label className="va-form__field">
                <span>Date de naissance</span>
                <input name="date_naissance" type="date" required />
              </label>
            </>
          )}
          <label className="va-form__field">
            <span>Email</span>
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <label className="va-form__field">
            <span>Mot de passe</span>
            <input name="password" type="password" required minLength={6} autoComplete={tab === 'login' ? 'current-password' : 'new-password'} />
          </label>

          {error && <div className="va-form__error">{error}</div>}

          <button type="submit" className="va-btn va-btn--primary va-btn--lg" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? 'Veuillez patienter…' : (tab === 'login' ? 'Se connecter' : 'Créer mon compte')}
          </button>
        </form>

        <div className="va-modal__switch">
          {tab === 'login' ? (
            <>Pas de compte ? <a onClick={() => setTab('signup')}>S&rsquo;inscrire</a></>
          ) : (
            <>Déjà un compte ? <a onClick={() => setTab('login')}>Se connecter</a></>
          )}
        </div>
      </div>
    </div>
  );
};

const WelcomeToast = ({ user, onDismiss }) => {
  const [leaving, setLeaving] = React.useState(false);
  React.useEffect(() => {
    const t = setTimeout(() => setLeaving(true), 4200);
    const t2 = setTimeout(() => onDismiss && onDismiss(), 4600);
    return () => { clearTimeout(t); clearTimeout(t2); };
  }, [onDismiss]);
  if (!user) return null;
  const initials = ((user.prenom || '')[0] || '') + ((user.nom || '')[0] || '');
  const isReturning = !!user.created_at && (Date.now() - new Date(user.created_at).getTime() > 60000);
  return (
    <div className={`va-toast ${leaving ? 'va-toast--leave' : ''}`} role="status">
      <div className="va-toast__avatar">
        {user.picture ? <img src={user.picture} alt="" /> : initials}
      </div>
      <div className="va-toast__body">
        <span className="va-toast__title">
          {isReturning ? 'Bon retour' : 'Bienvenue'}, {user.prenom} !
        </span>
        <span className="va-toast__sub">
          Vous êtes connecté{user.email ? ` · ${user.email}` : ''}.
        </span>
      </div>
      <button className="va-toast__close" onClick={() => { setLeaving(true); setTimeout(onDismiss, 240); }} aria-label="Fermer">
        <IClose size={14} />
      </button>
    </div>
  );
};

Object.assign(window, { useAuth, AuthModal, WelcomeToast, AUTH_STORAGE });
