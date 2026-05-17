/* Voyage Assistant — main app shell.
   Gère le routing, le theme, l'auth (useAuth) et l'AuthModal global. */

const ROUTES = ['home', 'results', 'booking', 'confirm', 'mes-billets', 'assistant'];

const useTheme = () => {
  const [mode, setMode] = React.useState(() => {
    try { return localStorage.getItem('va.theme') || 'light'; } catch { return 'light'; }
  });
  React.useEffect(() => {
    try { localStorage.setItem('va.theme', mode); } catch {}
  }, [mode]);
  const resolved = mode === 'system'
    ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : mode;
  return { mode, setMode, resolved };
};

const useRoute = () => {
  const [route, setRouteRaw] = React.useState(() => {
    try { return localStorage.getItem('va.route') || 'home'; } catch { return 'home'; }
  });
  const [ctx, setCtx] = React.useState(() => {
    try { return JSON.parse(localStorage.getItem('va.ctx') || '{}'); } catch { return {}; }
  });
  const go = React.useCallback((next, nextCtx) => {
    if (!ROUTES.includes(next)) next = 'home';
    setRouteRaw(next);
    if (nextCtx) setCtx((c) => ({ ...c, ...nextCtx }));
    try {
      localStorage.setItem('va.route', next);
      if (nextCtx) localStorage.setItem('va.ctx', JSON.stringify({ ...ctx, ...nextCtx }));
    } catch {}
    requestAnimationFrame(() => {
      const sc = document.querySelector('.va-app__main');
      if (sc) sc.scrollTo(0, 0);
    });
  }, [ctx]);
  return { route, ctx, go };
};

const UserChip = ({ user, onLogout, onGo }) => {
  const [open, setOpen] = React.useState(false);
  const initials = ((user.prenom || '')[0] || '') + ((user.nom || '')[0] || '');
  return (
    <div style={{ position: 'relative' }}>
      <button className="va-userchip" type="button" onClick={() => setOpen(o => !o)}>
        <span className="va-userchip__avatar">
          {user.picture ? <img src={user.picture} alt="" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : initials}
        </span>
        <span>{user.prenom}</span>
        <IChevronRight size={12} style={{ transform: 'rotate(90deg)', opacity: 0.5 }} />
      </button>
      {open && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 40 }} onClick={() => setOpen(false)} />
          <div className="va-usermenu">
            <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--va-border)', marginBottom: 4 }}>
              <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--va-text)' }}>{user.prenom} {user.nom}</div>
              <div style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{user.email}</div>
            </div>
            <button
              className="va-usermenu__item"
              onClick={() => { setOpen(false); onGo && onGo('mes-billets'); }}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <IFile size={14} /> Historique de mes billets
            </button>
            <div style={{ height: 1, background: 'var(--va-border)', margin: '4px 0' }} />
            <button className="va-usermenu__item" onClick={() => { setOpen(false); onLogout(); }}>
              Se déconnecter
            </button>
          </div>
        </>
      )}
    </div>
  );
};

const NavInt = ({ route, go, themeMode, setTheme, auth, onLogin }) => {
  const linkCls = (r) => 'va-navlink' + (route === r ? ' is-active' : '');
  return (
    <nav className="va-nav va-nav--bordered">
      <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
        <a onClick={() => go('home')} style={{ cursor: 'pointer' }}>
          <Wordmark />
        </a>
        <div className="va-nav__links">
          <a className={linkCls('home')}    onClick={() => go('home')}>Accueil</a>
          <a className={linkCls('results')} onClick={() => go('results')}>Destinations</a>
          <a className={linkCls('mes-billets')} onClick={() => go('mes-billets')}>Mes billets</a>
          <a className={linkCls('assistant')} onClick={() => go('assistant')}>Assistant</a>
        </div>
      </div>
      <div className="va-nav__right">
        <button className="va-iconbtn" title="Langue"><IGlobe size={18} /></button>
        <div className="va-themetoggle" aria-label="Thème">
          <button className={themeMode === 'light' ? 'is-active' : ''} title="Clair"  onClick={() => setTheme('light')}><ISun size={14} /></button>
          <button className={themeMode === 'dark'  ? 'is-active' : ''} title="Sombre" onClick={() => setTheme('dark')}><IMoon size={14} /></button>
          <button className={themeMode === 'system' ? 'is-active' : ''} title="Système" onClick={() => setTheme('system')}><IMonitor size={14} /></button>
        </div>
        {auth.isAuth ? (
          <UserChip user={auth.user} onLogout={auth.logout} onGo={go} />
        ) : (
          <button
            className="va-btn va-btn--sm va-btn--secondary"
            style={{ marginLeft: 6 }}
            onClick={() => onLogin('login')}
          >
            Se connecter
          </button>
        )}
      </div>
    </nav>
  );
};

const FloatingFAB = ({ go, route }) => {
  if (route === 'assistant') return null;
  return (
    <button className="va-fab" onClick={() => go('assistant')}>
      <span className="va-fab__avatar"><ISparkles size={16} /></span>
      Discuter avec l&rsquo;assistant
    </button>
  );
};

const VoyageApp = () => {
  const { mode: themeMode, setMode: setTheme, resolved } = useTheme();
  const { route, ctx, go } = useRoute();
  const auth = useAuth();
  window.VA_AUTH = auth;

  const [authModalOpen, setAuthModalOpen] = React.useState(false);
  const [authTab, setAuthTab] = React.useState('login');
  const [welcomeUser, setWelcomeUser] = React.useState(null);
  const openAuth = (tab = 'login') => { setAuthTab(tab); setAuthModalOpen(true); };

  let page;
  if (route === 'home')         page = <HomePage go={go} />;
  else if (route === 'results') page = <ResultsPage go={go} ctx={ctx} />;
  else if (route === 'booking') page = <BookingPage go={go} ctx={ctx} auth={auth} onRequestLogin={openAuth} />;
  else if (route === 'confirm') page = <ConfirmPage go={go} ctx={ctx} />;
  else if (route === 'mes-billets') page = <MesBilletsPage go={go} ctx={ctx} auth={auth} />;
  else if (route === 'assistant')   page = <InteractiveChat go={go} ctx={ctx} auth={auth} onRequestLogin={() => openAuth('login')} />;
  else page = <HomePage go={go} />;

  const isChat = route === 'assistant';

  return (
    <div className={`va ${resolved === 'dark' ? 'va-dark' : ''}`} data-screen-label={route}>
      <div className="va-app">
        <NavInt route={route} go={go} themeMode={themeMode} setTheme={setTheme} auth={auth} onLogin={openAuth} />
        <main className={`va-app__main${isChat ? ' va-app__main--chat' : ''}`} data-screen-label={`page-${route}`}>
          {page}
        </main>
        <FloatingFAB go={go} route={route} />
        <AuthModal
          open={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          defaultTab={authTab}
          onSuccess={(u) => setWelcomeUser(u)}
        />
        {welcomeUser && (
          <WelcomeToast user={welcomeUser} onDismiss={() => setWelcomeUser(null)} />
        )}
      </div>
    </div>
  );
};

Object.assign(window, { VoyageApp });
