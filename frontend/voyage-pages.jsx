/* Voyage Assistant — pages for the interactive prototype.
   Home, Results, Booking, Confirmation, MesBillets. Uses globals from
   voyage-icons.jsx + voyage-shared.jsx. */

/* ── Fake-QR generator (deterministic pseudo-random grid) ── */
const QRCode = ({ seed = 'TRV-2026-AX42K9', size = 120 }) => {
  const N = 21;
  // simple hash → 0/1 grid; finder patterns in 3 corners
  const cells = React.useMemo(() => {
    let h = 0; for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
    const rng = () => { h = (h * 1664525 + 1013904223) >>> 0; return h / 4294967295; };
    const g = Array.from({ length: N }, () => Array.from({ length: N }, () => rng() > 0.52 ? 1 : 0));
    // finder patterns
    const place = (r, c) => {
      for (let i = 0; i < 7; i++) for (let j = 0; j < 7; j++) g[r+i][c+j] = 0;
      for (let i = 0; i < 7; i++) { g[r][c+i] = 1; g[r+6][c+i] = 1; g[r+i][c] = 1; g[r+i][c+6] = 1; }
      for (let i = 2; i < 5; i++) for (let j = 2; j < 5; j++) g[r+i][c+j] = 1;
    };
    place(0, 0); place(0, N - 7); place(N - 7, 0);
    // timing lines
    for (let i = 8; i < N - 8; i++) { g[6][i] = i % 2 === 0 ? 1 : 0; g[i][6] = i % 2 === 0 ? 1 : 0; }
    return g;
  }, [seed]);
  const cell = size / N;
  return (
    <svg viewBox={`0 0 ${N} ${N}`} className="va-qrsvg">
      {cells.map((row, r) => row.map((v, c) => v ? <rect key={`${r}-${c}`} className="va-qrm" x={c} y={r} width={1} height={1} /> : null))}
    </svg>
  );
};

/* ──────────────────────────────────────────────────────────
   HOME — based on variant B (minimaliste) with subtle photo
   ──────────────────────────────────────────────────────── */

const SearchEditor = ({ values, onClose, onApply, onSearch }) => {
  const [v, setV] = React.useState(values);
  const apply = () => { onApply(v); onClose(); };
  const search = () => { onApply(v); onSearch(v); onClose(); };
  return (
    <div className="va-modal-overlay" onClick={(e) => { if (e.target.classList.contains('va-modal-overlay')) onClose(); }}>
      <div className="va-modal" style={{ maxWidth: 520 }}>
        <button className="va-modal__close" onClick={onClose} aria-label="Fermer"><IClose size={18} /></button>
        <h2 className="va-modal__title">Modifier la recherche</h2>
        <p className="va-modal__sub">Définissez votre trajet, on cherche les billets disponibles.</p>
        <div className="va-form">
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
            <TripTypeTabs value={v.tripType || 'aller'} onChange={(t) => setV({ ...v, tripType: t })} />
          </div>
          <div className="va-form__row">
            <div className="va-form__field">
              <span>Départ</span>
              <Autocomplete
                value={v.depart || ''}
                placeholder="Ville, gare, aéroport…"
                onChange={(val) => setV({ ...v, depart: val })}
                onPick={(it) => setV({ ...v, depart: it.nom })}
              />
            </div>
            <div className="va-form__field">
              <span>Arrivée</span>
              <Autocomplete
                value={v.arrivee || ''}
                placeholder="Ville, gare, aéroport…"
                onChange={(val) => setV({ ...v, arrivee: val })}
                onPick={(it) => setV({ ...v, arrivee: it.nom })}
              />
            </div>
          </div>
          <div className="va-form__row">
            <label className="va-form__field">
              <span>{isRoundTrip(v.tripType) ? 'Date aller' : v.tripType === 'retour' ? 'Date retour' : 'Date'}</span>
              <input type="date" value={v.date || ''} onChange={(e) => setV({ ...v, date: e.target.value })} />
            </label>
            {isRoundTrip(v.tripType) ? (
              <label className="va-form__field">
                <span>Date retour</span>
                <input type="date" value={v.dateRetour || ''} min={v.date || undefined}
                  onChange={(e) => setV({ ...v, dateRetour: e.target.value })} />
              </label>
            ) : (
              <div className="va-form__field" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--va-text-muted)' }}>Voyageurs</span>
                <PaxStepper
                  value={normalizePax(v)}
                  onChange={(pax) => setV({ ...v, pax, passagers: paxCount(pax) })}
                />
              </div>
            )}
          </div>
          {isRoundTrip(v.tripType) && (
            <div className="va-form__row">
              <div className="va-form__field" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--va-text-muted)' }}>Voyageurs</span>
                <PaxStepper
                  value={normalizePax(v)}
                  onChange={(pax) => setV({ ...v, pax, passagers: paxCount(pax) })}
                />
              </div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
          <button className="va-btn va-btn--sm va-btn--secondary" onClick={onClose} type="button">Annuler</button>
          <button className="va-btn va-btn--sm" onClick={apply} type="button" style={{ background: 'var(--va-surface-2)' }}>
            Mettre à jour
          </button>
          <button className="va-btn va-btn--sm va-btn--primary" onClick={search} type="button">
            <ISearch size={14} /> Rechercher
          </button>
        </div>
      </div>
    </div>
  );
};

const HomePage = ({ go }) => {
  const [mode, setMode] = React.useState('all');
  const [search, setSearch] = React.useState({
    depart: 'Paris', arrivee: 'Marseille',
    date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
    dateRetour: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
    tripType: 'aller',
    pax: { adultes: 1, enfants: 0, bebes: 0 },
  });
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [dbStats, setDbStats] = React.useState(null);

  React.useEffect(() => {
    fetch(`${window.VA_CONFIG.API_BASE}/stats`)
      .then(r => r.json())
      .then(d => setDbStats(d))
      .catch(() => {});
  }, []);

  return (
  <div className="va-anim-in">
    <section className="va-hero-b">
      <span className="va-hero-b__eyebrow">Voyage Assistant — réservation multi-mode</span>
      <h1 className="va-hero-b__title">
        Où voulez-vous<br />
        <em>aller cette saison&nbsp;?</em>
      </h1>
      <p className="va-hero-b__lead">
        Avion, train, bateau, bus longue distance. Comparez{' '}
        {dbStats ? dbStats.compagnies.toLocaleString('fr-FR') : '…'}{' '}
        compagnies en un seul écran,
        gérez ensuite vos billets avec un assistant qui ne dort jamais.
      </p>
      <ModeTabs active={mode} onSelect={setMode} />
      <div className="va-hero-b__search">
        <SearchBarEditable
          values={search}
          type={MODE_KEY_TO_API[mode]}
          onChange={setSearch}
          onSearch={(v) => go('results', { search: { ...v, type: MODE_KEY_TO_API[mode] } })}
        />
      </div>
      <div className="va-hero-b__stats">
        <div><strong>{dbStats ? dbStats.destinations.toLocaleString('fr-FR') : '…'}</strong>destinations</div>
        <div style={{ width: 1, height: 24, background: 'var(--va-border)' }}></div>
        <div><strong>{dbStats ? dbStats.compagnies.toLocaleString('fr-FR') : '…'}</strong>compagnies</div>
        <div style={{ width: 1, height: 24, background: 'var(--va-border)' }}></div>
        <div><strong>2,4 min</strong>réservation moyenne</div>
        <div style={{ width: 1, height: 24, background: 'var(--va-border)' }}></div>
        <div><strong>24 / 7</strong>assistance</div>
      </div>
    </section>

    <section className="va-section" style={{ marginTop: 28 }}>
      <ValueProps />
    </section>

    <section className="va-section" style={{ marginTop: 56 }}>
      <div className="va-section__head">
        <div>
          <div className="va-section__title">Destinations qui appellent</div>
          <div className="va-section__sub">Sélection éditoriale, départ depuis Paris cette semaine.</div>
        </div>
        <a className="va-section__link" style={{ cursor: 'pointer' }} onClick={() => go('results', { search: { ...search, type: MODE_KEY_TO_API[mode] } })}>
          Voir tout <IArrowRight size={14} />
        </a>
      </div>
      <DestinationsCarousel
        perPage={4}
        onPick={(d) => go('results', {
          search: { depart: 'Paris', arrivee: d.city, date: search.date, dateRetour: search.dateRetour, tripType: search.tripType, pax: search.pax, type: MODE_KEY_TO_API[mode] },
        })}
      />
    </section>

    <section className="va-section" style={{ marginTop: 56, paddingBottom: 80 }}>
      <div style={{
        background: 'var(--va-surface)', border: '1px solid var(--va-border)',
        borderRadius: 'var(--va-radius-xl)', padding: 36,
        display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 28,
      }}>
        <div>
          <div className="va-eyebrow" style={{ color: 'var(--va-accent)', marginBottom: 12 }}>Nouveau — Assistant IA</div>
          <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--va-text)', marginBottom: 8, textWrap: 'balance' }}>
            Un retard, une modif, une réclamation&nbsp;? Demandez à l&rsquo;assistant.
          </div>
          <div style={{ fontSize: 14.5, color: 'var(--va-text-muted)', maxWidth: 560, lineHeight: 1.55 }}>
            Il consulte votre billet après une rapide vérification d&rsquo;identité,
            puis exécute la démarche à votre place — en moyenne en 1 min 40.
          </div>
        </div>
        <button className="va-btn va-btn--primary va-btn--lg" onClick={() => go('assistant')}>
          <IMessage size={16} /> Parler à l&rsquo;assistant
        </button>
      </div>
    </section>
  </div>
  );
};

/* ──────────────────────────────────────────────────────────
   RÉSULTATS
   ──────────────────────────────────────────────────────── */

const MODE_ICONS = { plane: IPlane, train: ITrain, ship: IShip, bus: IBus };

/* Points intermédiaires sur la ligne de trajet selon le nombre d'escales */
const StopDots = ({ stops }) => {
  const n = stops === '2 escales' ? 2 : stops === '1 escale' ? 1 : 0;
  if (n === 0) return null;
  const positions = n === 1 ? ['50%'] : ['33%', '67%'];
  return positions.map((left, i) => (
    React.createElement('span', {
      key: i,
      style: {
        position: 'absolute', top: '50%', left,
        width: 7, height: 7, borderRadius: '50%',
        background: 'var(--va-accent)',
        border: '2px solid var(--va-surface)',
        transform: 'translate(-50%, -50%)',
        zIndex: 2,
      },
    })
  ));
};

const RouteCard = ({ r, onSelect }) => {
  const Icon = MODE_ICONS[r.mode] || ITrain;
  return (
    <div className="va-route" onClick={() => onSelect(r)}>
      <div className="va-route__brand"><Icon size={26} /></div>
      <div className="va-route__main">
        <div className="va-route__stop">
          <div className="va-route__time">{r.depart}</div>
          <div className="va-route__city">{r.from}</div>
        </div>
        <div className="va-route__path">
          <div>{r.dur}</div>
          <div className="va-route__path-line">
            <span className="va-route__path-icon"><Icon size={13} /></span>
            <StopDots stops={r.stops} />
          </div>
          <div style={{ color: r.escales && r.escales.length > 0 ? 'var(--va-accent)' : undefined }}>
            {r.stops}
          </div>
          {r.escales && r.escales.length > 0 && (
            <div style={{ fontSize: 10, color: 'var(--va-text-muted)', marginTop: 1 }}>
              via {r.escales.join(' · ')}
            </div>
          )}
        </div>
        <div className="va-route__stop va-route__stop--right">
          <div className="va-route__time">{r.arrive}</div>
          <div className="va-route__city">{r.to}</div>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
        <div className="va-route__meta">
          <div className="va-route__company">{r.company}</div>
          <div className="va-route__class">{r.class}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="va-route__price">{r.price}<small> €</small></div>
          <div className="va-route__sub">par voyageur</div>
        </div>
        <div className="va-route__tags">
          {r.tags.map((t, i) => (
            <span key={i} className={`va-route__tag ${t.good ? 'va-route__tag--good' : ''}`}>
              {t.good && <ICheck size={11} strokeWidth={2.2} />}
              {t.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

const Checkrow = ({ label, count, active, onClick }) => (
  <button className={`va-checkrow ${active ? 'is-on' : ''}`} onClick={onClick}
    style={{ background: 'transparent', border: 'none', padding: 0, textAlign: 'left', width: '100%', fontFamily: 'inherit' }}>
    <span className="va-checkrow__box"><ICheck size={10} strokeWidth={3} /></span>
    <span>{label}</span>
    {count != null && <span className="va-checkrow__count">{count}</span>}
  </button>
);

const EditSearchPopover = ({ values, onClose, onApply }) => {
  const [v, setV] = React.useState(values);
  return (
    <div className="va-edit-popover">
      <h4>Modifier la recherche</h4>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
        <TripTypeTabs value={v.tripType || 'aller'} onChange={(t) => setV({ ...v, tripType: t })} />
      </div>
      <div className="va-edit-popover__row">
        <div className="va-form__field">
          <span>Départ</span>
          <Autocomplete
            value={v.depart || ''}
            placeholder="Ville, gare, aéroport…"
            onChange={(val) => setV({ ...v, depart: val })}
            onPick={(it) => setV({ ...v, depart: it.nom })}
          />
        </div>
        <div className="va-form__field">
          <span>Arrivée</span>
          <Autocomplete
            value={v.arrivee || ''}
            placeholder="Ville, gare, aéroport…"
            onChange={(val) => setV({ ...v, arrivee: val })}
            onPick={(it) => setV({ ...v, arrivee: it.nom })}
          />
        </div>
      </div>
      <div className="va-edit-popover__row">
        <label className="va-form__field">
          <span>{isRoundTrip(v.tripType) ? 'Date aller' : v.tripType === 'retour' ? 'Date retour' : 'Date'}</span>
          <input type="date" value={v.date || ''} onChange={(e) => setV({ ...v, date: e.target.value })} />
        </label>
        {isRoundTrip(v.tripType) ? (
          <label className="va-form__field">
            <span>Date retour</span>
            <input type="date" value={v.dateRetour || ''} min={v.date || undefined}
              onChange={(e) => setV({ ...v, dateRetour: e.target.value })} />
          </label>
        ) : (
          <div className="va-form__field" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span>Voyageurs</span>
            <PaxStepper
              value={normalizePax(v)}
              onChange={(pax) => setV({ ...v, pax, passagers: paxCount(pax) })}
            />
          </div>
        )}
      </div>
      {isRoundTrip(v.tripType) && (
        <div className="va-edit-popover__row">
          <div className="va-form__field" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span>Voyageurs</span>
            <PaxStepper
              value={normalizePax(v)}
              onChange={(pax) => setV({ ...v, pax, passagers: paxCount(pax) })}
            />
          </div>
        </div>
      )}
      <div className="va-edit-popover__actions">
        <button className="va-btn va-btn--sm va-btn--secondary" onClick={onClose} type="button">Annuler</button>
        <button className="va-btn va-btn--sm va-btn--primary" onClick={() => { onApply(v); onClose(); }} type="button">
          Appliquer
        </button>
      </div>
    </div>
  );
};

const ResultsPage = ({ go, ctx }) => {
  const search = (ctx && ctx.search) || {
    depart: 'Paris', arrivee: 'Marseille',
    date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
    pax: { adultes: 1, enfants: 0, bebes: 0 }, type: null,
  };
  const [trajets, setTrajets] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [editOpen, setEditOpen] = React.useState(false);
  const [currentSearch, setCurrentSearch] = React.useState(search);
  const [fallback, setFallback] = React.useState(false);

  // Récupère TOUS les modes pour la recherche départ/arrivée donnée
  // (le filtre par mode est appliqué côté client via les checkboxes sidebar)
  React.useEffect(() => {
    setLoading(true);
    setFallback(false);
    // 1) Recherche exacte sans filtre type
    window.VA_API.searchTrajets({
      depart: currentSearch.depart || undefined,
      arrivee: currentSearch.arrivee || undefined,
    })
      .then((data) => {
        if (!data || data.length === 0) {
          // 2) Fallback : on relâche la destination
          setFallback(true);
          return window.VA_API.searchTrajets({ depart: currentSearch.depart || undefined });
        }
        return data;
      })
      .then((data) => {
        if (!data || data.length === 0) {
          // 3) Fallback total
          return window.VA_API.searchTrajets({});
        }
        return data;
      })
      .then((data) => { setTrajets(data || []); setBudgetMax(null); })
      .catch(() => setTrajets([]))
      .finally(() => setLoading(false));
  }, [currentSearch.depart, currentSearch.arrivee]);

  // Convertit un trajet API en format RouteCard avec tags générés
  const enrich = (t) => {
    const modeKey = MODE_API_TO_KEY[t.type] || 'train';
    const depart = new Date(t.date_depart);
    const arrive = new Date(t.date_arrivee);
    const hh = (d) => `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
    const mins = Math.round((arrive - depart) / 60000);
    const dur = `${Math.floor(mins / 60)} h ${String(mins % 60).padStart(2,'0')}`;
    const tags = [];
    if (t.has_wifi) tags.push({ label: 'Wi-Fi', good: false });
    if (t.has_prise) tags.push({ label: 'Prise', good: false });
    if (t.type === 'train' || t.type === 'bus') tags.push({ label: 'Émission –93 %', good: true });
    if (t.prix < 35) tags.push({ label: 'Petit prix', good: true });
    if (t.retard_minutes > 0) tags.push({ label: `Retard ${t.retard_minutes} min`, good: false });
    return {
      id: t.id, _api: t,
      company: t.compagnie, class: t.classe || 'Standard',
      depart: hh(depart), arrive: hh(arrive),
      from: t.depart, to: t.arrivee,
      dur, stops: t.stops || 'direct',
      escales: t.escales || [],
      dureeEscaleMin: t.duree_escale_min || 0,
      price: Math.round(t.prix), mode: modeKey,
      tags,
    };
  };

  const [sort, setSort] = React.useState('best');
  const [budgetMax, setBudgetMax] = React.useState(null); // null = no filter applied yet
  const initialModeKey = currentSearch.type ? MODE_API_TO_KEY[currentSearch.type] : null;
  const allModesOn = {
    train: true, plane: true, bus: true, ship: true,
    direct: true, oneStop: true, twoStops: true,
    morning: true, afternoon: true, evening: true,
  };
  const [filters, setFilters] = React.useState(() => {
    if (initialModeKey) {
      return {
        train: initialModeKey === 'train', plane: initialModeKey === 'plane',
        bus: initialModeKey === 'bus',     ship: initialModeKey === 'ship',
        direct: true, oneStop: true, twoStops: true,
        morning: true, afternoon: true, evening: true,
      };
    }
    return allModesOn;
  });
  const toggle = (k) => setFilters((f) => ({ ...f, [k]: !f[k] }));
  const resetFilters = () => setFilters(allModesOn);
  const [userTouchedFilters, setUserTouchedFilters] = React.useState(false);
  const toggleSmart = (k) => { setUserTouchedFilters(true); toggle(k); };

  // Auto-élargissement : si après chargement des trajets le mode initial n'a aucun trajet,
  // on bascule sur "tous les modes" automatiquement pour ne pas afficher une page vide.
  React.useEffect(() => {
    if (loading || userTouchedFilters || !trajets || trajets.length === 0) return;
    const modeKeys = ['train', 'plane', 'bus', 'ship'];
    const visible = trajets.map(t => MODE_API_TO_KEY[t.type] || 'train').filter(m => filters[m]).length;
    if (visible === 0) setFilters(allModesOn);
  }, [loading, trajets, userTouchedFilters]);

  const timeSlot = (hhmm) => {
    const h = parseInt(hhmm.split(':')[0], 10);
    if (h >= 6  && h < 12) return 'morning';
    if (h >= 12 && h < 18) return 'afternoon';
    if (h >= 18)            return 'evening';
    return 'night';
  };

  const sorted = React.useMemo(() => {
    const src = (trajets || []).map(enrich).filter(r => {
      if (!filters[r.mode]) return false;
      const slot = timeSlot(r.depart);
      if (slot === 'morning'   && !filters.morning)   return false;
      if (slot === 'afternoon' && !filters.afternoon) return false;
      if (slot === 'evening'   && !filters.evening)   return false;
      if (r.stops === 'direct'  && !filters.direct)   return false;
      if (r.stops === '1 escale' && !filters.oneStop)  return false;
      if (r.stops === '2 escales' && !filters.twoStops) return false;
      if (r.stops !== 'direct' && r.stops !== '1 escale' && r.stops !== '2 escales' && !filters.oneStop) return false;
      if (budgetMax !== null && r.price > budgetMax) return false;
      return true;
    });
    if (sort === 'cheap') return [...src].sort((a, b) => a.price - b.price);
    if (sort === 'fast')  return [...src].sort((a, b) => a.dur.localeCompare(b.dur));
    if (sort === 'early') return [...src].sort((a, b) => a.depart.localeCompare(b.depart));
    return src;
  }, [sort, filters, trajets, budgetMax]);

  const counts = React.useMemo(() => {
    const all = (trajets || []).map(enrich);
    return {
      train:     all.filter(r => r.mode === 'train').length,
      plane:     all.filter(r => r.mode === 'plane').length,
      bus:       all.filter(r => r.mode === 'bus').length,
      ship:      all.filter(r => r.mode === 'ship').length,
      morning:   all.filter(r => timeSlot(r.depart) === 'morning').length,
      afternoon: all.filter(r => timeSlot(r.depart) === 'afternoon').length,
      evening:   all.filter(r => timeSlot(r.depart) === 'evening').length,
      direct:    all.filter(r => r.stops === 'direct').length,
      oneStop:   all.filter(r => r.stops === '1 escale').length,
      twoStops:  all.filter(r => r.stops === '2 escales').length,
      priceMin:  all.length ? Math.min(...all.map(r => r.price)) : 0,
      priceMax:  all.length ? Math.max(...all.map(r => r.price)) : 9999,
    };
  }, [trajets]);

  return (
    <div className="va-anim-in">
      <div className="va-pagehead">
        <div className="va-pagehead__top">
          <div className="va-crumb">
            <a onClick={() => go('home')}>Accueil</a>
            <span className="va-crumb__sep">/</span>
            <span className="va-crumb__current">Trajets disponibles</span>
          </div>
          <div className="va-stepper">
            <div className="va-stepper__item is-done"><span className="va-stepper__num"><ICheck size={11} strokeWidth={3} /></span><span className="va-stepper__label">Recherche</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item is-active"><span className="va-stepper__num">2</span><span className="va-stepper__label">Trajet</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item"><span className="va-stepper__num">3</span><span className="va-stepper__label">Voyageurs</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item"><span className="va-stepper__num">4</span><span className="va-stepper__label">Confirmation</span></div>
          </div>
        </div>
        <h1 className="va-pagehead__title">
          {currentSearch.depart} → {currentSearch.arrivee} · {currentSearch.date}
          {isRoundTrip(currentSearch.tripType) && currentSearch.dateRetour && ` ↔ ${currentSearch.dateRetour}`}
        </h1>
        <div className="va-recap" style={{ position: 'relative' }}>
          <span className="va-recap__pill">{tripTypeLabel(currentSearch.tripType)}</span>
          <span className="va-recap__sep"></span>
          <span className="va-recap__pill"><IMapPin size={14} /> {currentSearch.depart}</span>
          <span className="va-recap__sep"></span>
          <span className="va-recap__pill"><IMapPin size={14} /> {currentSearch.arrivee}</span>
          <span className="va-recap__sep"></span>
          <span className="va-recap__pill"><ICalendar size={14} /> {currentSearch.date}</span>
          {isRoundTrip(currentSearch.tripType) && currentSearch.dateRetour && (
            <>
              <span className="va-recap__sep"></span>
              <span className="va-recap__pill"><ICalendar size={14} /> retour {currentSearch.dateRetour}</span>
            </>
          )}
          <span className="va-recap__sep"></span>
          <span className="va-recap__pill" title={paxBreakdown(normalizePax(currentSearch))}><IUsers size={14} /> {paxLabel(normalizePax(currentSearch))}</span>
          <button className="va-recap__edit" onClick={() => setEditOpen(v => !v)} type="button">
            <IEdit size={12} /> Modifier
          </button>
          {editOpen && (
            <EditSearchPopover
              values={currentSearch}
              onClose={() => setEditOpen(false)}
              onApply={(v) => setCurrentSearch(v)}
            />
          )}
        </div>
      </div>

      <div className="va-results">
        <aside className="va-filters">
          <div className="va-filter">
            <div className="va-filter__title">
              Mode de transport
              <small>{Object.entries(counts).filter(([k,v]) => ['train','plane','bus','ship'].includes(k) && v > 0).length}</small>
            </div>
            <div className="va-filter__rows">
              <Checkrow label="Train"  count={counts.train} active={filters.train} onClick={() => toggleSmart('train')} />
              <Checkrow label="Avion"  count={counts.plane} active={filters.plane} onClick={() => toggleSmart('plane')} />
              <Checkrow label="Bus"    count={counts.bus}   active={filters.bus}   onClick={() => toggleSmart('bus')} />
              <Checkrow label="Bateau" count={counts.ship}  active={filters.ship}  onClick={() => toggleSmart('ship')} />
            </div>
          </div>

          <div className="va-filter">
            <div className="va-filter__title">Budget</div>
            <div className="va-range">
              <input
                type="range"
                min={counts.priceMin}
                max={counts.priceMax}
                value={budgetMax !== null ? budgetMax : counts.priceMax}
                onChange={e => setBudgetMax(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--va-primary)', cursor: 'pointer' }}
              />
              <div className="va-range__bounds">
                <span><strong>{counts.priceMin} €</strong></span>
                <span><strong>{budgetMax !== null ? budgetMax : counts.priceMax} €</strong></span>
              </div>
            </div>
          </div>

          <div className="va-filter">
            <div className="va-filter__title">Horaire de départ</div>
            <div className="va-filter__rows">
              <Checkrow label="Matin (06:00 – 12:00)"      count={counts.morning}   active={filters.morning}   onClick={() => toggle('morning')} />
              <Checkrow label="Après-midi (12:00 – 18:00)" count={counts.afternoon} active={filters.afternoon} onClick={() => toggle('afternoon')} />
              <Checkrow label="Soir (18:00 – 24:00)"       count={counts.evening}   active={filters.evening}   onClick={() => toggle('evening')} />
            </div>
          </div>

          <div className="va-filter">
            <div className="va-filter__title">Escales</div>
            <div className="va-filter__rows">
              <Checkrow label="Direct"   count={counts.direct}   active={filters.direct}   onClick={() => toggleSmart('direct')} />
              <Checkrow label="1 escale" count={counts.oneStop}  active={filters.oneStop}  onClick={() => toggleSmart('oneStop')} />
              <Checkrow label="2 escales" count={counts.twoStops} active={filters.twoStops} onClick={() => toggleSmart('twoStops')} />
            </div>
          </div>
        </aside>

        <div>
          {fallback && trajets && trajets.length > 0 && (
            <div style={{
              padding: '14px 18px', marginBottom: 18, borderRadius: 'var(--va-radius-md)',
              background: 'rgba(217, 119, 87, 0.12)', border: '2px solid var(--va-accent)',
              color: 'var(--va-text)',
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <IAlert size={20} style={{ color: 'var(--va-accent)', flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
                    Désolé — aucun trajet trouvé pour {currentSearch.depart} → <strong>{currentSearch.arrivee}</strong>
                  </div>
                  <div style={{ fontSize: 13.5, color: 'var(--va-text-muted)', lineHeight: 1.5 }}>
                    Cette destination n’est pas (encore) dans notre catalogue, ou aucun trajet n’est programmé.
                    Voici d’<strong>autres destinations</strong> au départ de <strong>{currentSearch.depart}</strong> —
                    ces trajets ne vont <strong>pas</strong> à {currentSearch.arrivee}.
                  </div>
                  <button
                    type="button"
                    className="va-btn va-btn--sm va-btn--secondary"
                    style={{ marginTop: 10 }}
                    onClick={() => setEditOpen(true)}
                  >
                    Modifier la recherche
                  </button>
                </div>
              </div>
            </div>
          )}
          {!loading && (trajets && trajets.length > 0) && sorted.length === 0 && (
            <div style={{
              padding: '12px 16px', marginBottom: 16, borderRadius: 'var(--va-radius-md)',
              background: 'var(--va-surface-2)', border: '1px solid var(--va-border)',
              fontSize: 13.5, color: 'var(--va-text)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
            }}>
              <span><strong>{trajets.length}</strong> trajets disponibles mais cachés par vos filtres.</span>
              <button className="va-btn va-btn--sm va-btn--secondary" onClick={resetFilters} type="button">
                Réinitialiser les filtres
              </button>
            </div>
          )}
          <div className="va-resultbar">
            <div className="va-resultbar__count">
              <strong>{sorted.length} trajets</strong>
              {sorted.length > 0 && <em>· dès {Math.min(...sorted.map(r => r.price))} €</em>}
            </div>
            <div className="va-sort">
              {[
                ['best', 'Meilleur'],
                ['cheap', 'Moins cher'],
                ['fast', 'Plus rapide'],
                ['early', 'Départ tôt'],
              ].map(([k, l]) => (
                <button key={k} className={sort === k ? 'is-active' : ''} onClick={() => setSort(k)}>{l}</button>
              ))}
            </div>
          </div>

          <div className="va-resultlist">
            {loading && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--va-text-muted)' }}>
                Recherche en cours…
              </div>
            )}
            {!loading && sorted.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--va-text-muted)' }}>
                Aucun trajet trouvé. Essayez d&rsquo;élargir vos critères.
              </div>
            )}
            {!loading && sorted.map((r) => (
              <RouteCard key={r.id} r={r} onSelect={(route) => { go('booking', { route, search: currentSearch }); }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ──────────────────────────────────────────────────────────
   RÉSERVATION (booking detail + form)
   ──────────────────────────────────────────────────────── */
const BOOKING_PHOTO = 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1400&q=85&auto=format';

const BookingPage = ({ go, ctx, auth, onRequestLogin }) => {
  const r = ctx && ctx.route;
  if (!r) { React.useEffect(() => go('home'), []); return null; }
  const Icon = MODE_ICONS[r.mode] || ITrain;
  const u = auth && auth.user;
  const sCtx = (ctx && ctx.search) || {};
  const pax = normalizePax(sCtx);
  const tripType = sCtx.tripType || 'aller';
  const dateRetour = sCtx.dateRetour;
  const classOpts = CLASS_OPTIONS[r.mode] || CLASS_OPTIONS.train;
  const bagOpts   = BAG_OPTIONS[r.mode]   || [];
  const [classId, setClassId] = React.useState(() => guessClassId(r.class, r.mode) || classOpts[0].id);
  const [bags, setBags] = React.useState(() => Object.fromEntries(bagOpts.map(b => [b.id, 0])));
  const totals = computeBookingTotal({ basePrice: r.price, mode: r.mode, pax, classId, bags, tripType });
  const [form, setForm] = React.useState({
    nom: u ? u.nom : '',
    prenom: u ? u.prenom : '',
    dob: '',
    email: u ? u.email : '',
    tel: '',
  });
  React.useEffect(() => {
    if (u) setForm((f) => ({ ...f, nom: u.nom, prenom: u.prenom, email: u.email }));
  }, [u && u.id]);
  const setField = (k) => (e) => { setError(null); setForm((f) => ({ ...f, [k]: e.target.value })); };
  // tel est optionnel côté backend, on ne l'exige plus côté front
  const requiredOk = form.nom && form.prenom && form.dob && form.email;
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const dobToISO = (s) => {
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const m = s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
    if (m) return `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`;
    return null;
  };

  const confirmAndPay = async () => {
    setError(null);
    if (!auth || !auth.isAuth) { onRequestLogin && onRequestLogin('signup'); return; }
    const missing = [];
    if (!form.nom) missing.push('Nom');
    if (!form.prenom) missing.push('Prénom');
    if (!form.dob) missing.push('Date de naissance');
    if (!form.email) missing.push('Email');
    if (missing.length) {
      setError(`Merci de remplir : ${missing.join(', ')}.`);
      return;
    }
    const dob = dobToISO(form.dob);
    if (!dob) { setError("Date de naissance invalide (utiliser JJ/MM/AAAA)."); return; }
    if (!r._api || !r._api.id) {
      go('confirm', { route: r, form, totals, pax, classId, bags });
      return;
    }
    setBusy(true);
    try {
      const billet = await window.VA_API.createBillet({
        trajet_id: r._api.id,
        voyageur: {
          nom: form.nom, prenom: form.prenom,
          date_naissance: dob, email: form.email,
          telephone: form.tel || null,
        },
        prix_paye: totals.total,
        classe: totals.cls.label,
        nb_places: pax.adultes + pax.enfants,
      });
      go('confirm', { route: r, form, billet, ticketNum: billet.numero_billet, totals, pax, classId, bags });
    } catch (e) {
      setError(`Erreur de réservation : ${e.message}`);
    } finally { setBusy(false); }
  };

  return (
    <div className="va-anim-in">
      <div className="va-pagehead">
        <div className="va-pagehead__top">
          <div className="va-crumb">
            <a onClick={() => go('home')}>Accueil</a>
            <span className="va-crumb__sep">/</span>
            <a onClick={() => go('results')}>Résultats</a>
            <span className="va-crumb__sep">/</span>
            <span className="va-crumb__current">Réservation</span>
          </div>
          <div className="va-stepper">
            <div className="va-stepper__item is-done"><span className="va-stepper__num"><ICheck size={11} strokeWidth={3} /></span><span className="va-stepper__label">Recherche</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item is-done"><span className="va-stepper__num"><ICheck size={11} strokeWidth={3} /></span><span className="va-stepper__label">Trajet</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item is-active"><span className="va-stepper__num">3</span><span className="va-stepper__label">Voyageurs</span></div>
            <span className="va-stepper__line"></span>
            <div className="va-stepper__item"><span className="va-stepper__num">4</span><span className="va-stepper__label">Confirmation</span></div>
          </div>
        </div>
      </div>

      <div className="va-booking">
        <div>
          <div className="va-booking__hero" style={{ backgroundImage: `url(${BOOKING_PHOTO})` }}>
            <div className="va-booking__heroCap">
              <div>
                <small>Trajet · {r.mode === 'plane' ? 'Vol' : r.mode === 'bus' ? 'Bus longue distance' : r.mode === 'ship' ? 'Bateau' : 'Train'} {r.company}</small>
                <h2>{r.from.split(' ')[0]} → {r.to.split(' ')[0]}</h2>
              </div>
              <span className="va-booking__heroBadge">Samedi 13 juin 2026</span>
            </div>
          </div>

          <div className="va-card" style={{ marginBottom: 18 }}>
            <div className="va-detailroute">
              <div className="va-detailroute__stop">
                <div className="va-detailroute__time">{r.depart}</div>
                <div className="va-detailroute__date">Sam. 13 juin 2026</div>
                <div className="va-detailroute__city">{r.from}</div>
                <div className="va-detailroute__sub">{r.from.includes('CDG') ? 'Terminal 2F' : 'Hall 2 · Voie L'}</div>
              </div>
              <div className="va-detailroute__sep">
                <div>{r.dur}</div>
                <div className="va-detailroute__sep-line"><StopDots stops={r.stops} /></div>
                <div style={{ color: r.escales && r.escales.length > 0 ? 'var(--va-accent)' : undefined }}>{r.stops}</div>
                {r.escales && r.escales.length > 0 && <div style={{ fontSize: 10, color: 'var(--va-text-muted)' }}>via {r.escales.join(' · ')}</div>}
              </div>
              <div className="va-detailroute__stop va-detailroute__stop--right">
                <div className="va-detailroute__time">{r.arrive}</div>
                <div className="va-detailroute__date">Sam. 13 juin 2026</div>
                <div className="va-detailroute__city">{r.to}</div>
                <div className="va-detailroute__sub">{r.to.includes('LYS') ? 'Terminal 1' : 'Voie 3'}</div>
              </div>
            </div>
            <div className="va-inforow">
              <div>
                <span className="va-inforow__label">Compagnie</span>
                <span className="va-inforow__value"><Icon size={14} /> {r.company}</span>
              </div>
              <div>
                <span className="va-inforow__label">Classe / tarif</span>
                <span className="va-inforow__value">{r.class}</span>
              </div>
              <div>
                <span className="va-inforow__label">Échange</span>
                <span className="va-inforow__value">Avant J–1</span>
              </div>
              <div>
                <span className="va-inforow__label">Remboursement</span>
                <span className="va-inforow__value">Partiel</span>
              </div>
            </div>
          </div>

          {/* Sélection de classe */}
          <div className="va-card" style={{ marginBottom: 18 }}>
            <div>
              <div className="va-card__title">Choisissez votre classe</div>
              <div className="va-card__sub">Le tarif s’adapte au confort et aux services inclus.</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(classOpts.length, 4)}, 1fr)`, gap: 12, marginTop: 14 }}>
              {classOpts.map((c) => {
                const sel = classId === c.id;
                const adultPrice = Math.round(r.price * c.mult);
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setClassId(c.id)}
                    style={{
                      textAlign: 'left', padding: 14, borderRadius: 12, cursor: 'pointer',
                      border: sel ? '2px solid var(--va-accent)' : '1px solid var(--va-border)',
                      background: sel ? 'rgba(217, 119, 87, 0.06)' : 'var(--va-surface)',
                      fontFamily: 'inherit',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--va-text)' }}>{c.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--va-text-muted)', marginTop: 4, minHeight: 32 }}>{c.sub}</div>
                    <div style={{ marginTop: 8, fontSize: 13, color: sel ? 'var(--va-accent)' : 'var(--va-text)', fontWeight: 600 }}>
                      {adultPrice} € <span style={{ fontWeight: 400, color: 'var(--va-text-muted)' }}>/ adulte</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bagages */}
          <div className="va-card" style={{ marginBottom: 18 }}>
            <div>
              <div className="va-card__title">Bagages</div>
              <div className="va-card__sub">{BAG_INCLUDED_LABEL}</div>
            </div>
            {bagOpts.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--va-text-muted)', marginTop: 10 }}>
                {r.mode === 'train' ? 'En train : bagages illimités inclus dans la limite de ce que vous portez.' :
                 r.mode === 'ship' ? 'À bord : bagages illimités inclus selon votre cabine.' :
                 'Aucune option de bagage supplémentaire pour ce mode.'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
                {bagOpts.map((b) => (
                  <div
                    key={b.id}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: 12, border: '1px solid var(--va-border)', borderRadius: 10,
                      background: bags[b.id] ? 'rgba(217, 119, 87, 0.06)' : 'transparent',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--va-text)' }}>{b.label}</div>
                      <div style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{b.sub} · {b.price} € / pièce</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <StepBtn onClick={() => setBags((bb) => ({ ...bb, [b.id]: Math.max(0, (bb[b.id] || 0) - 1) }))} disabled={(bags[b.id] || 0) <= 0}>−</StepBtn>
                      <span style={{ minWidth: 16, textAlign: 'center', fontWeight: 600, color: 'var(--va-text)' }}>{bags[b.id] || 0}</span>
                      <StepBtn onClick={() => setBags((bb) => ({ ...bb, [b.id]: (bb[b.id] || 0) + 1 }))}>+</StepBtn>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="va-card">
            <div>
              <div className="va-card__title">Voyageur principal</div>
              <div className="va-card__sub">Ces informations figureront sur le billet. Aucune création de compte requise.</div>
            </div>
            <div className="va-form">
              <div className="va-form__row">
                <div className="va-field">
                  <label className="va-field__label">Nom <sup>*</sup></label>
                  <input className="va-input" value={form.nom} onChange={setField('nom')} />
                </div>
                <div className="va-field">
                  <label className="va-field__label">Prénom <sup>*</sup></label>
                  <input className="va-input" value={form.prenom} onChange={setField('prenom')} />
                </div>
              </div>
              <div className="va-form__row">
                <div className="va-field">
                  <label className="va-field__label">Date de naissance <sup>*</sup></label>
                  <div className="va-input-wrap">
                    <span className="va-input-wrap__icon"><ICalendar size={16} /></span>
                    <input className="va-input va-input--with-icon" value={form.dob} onChange={setField('dob')} placeholder="JJ/MM/AAAA" />
                  </div>
                </div>
                <div className="va-field">
                  <label className="va-field__label">Téléphone <small style={{ color: 'var(--va-text-muted)', fontWeight: 400 }}>(optionnel)</small></label>
                  <input className="va-input" value={form.tel} onChange={setField('tel')} placeholder="06 12 34 56 78" />
                </div>
              </div>
              <div className="va-form__row va-form__row--full">
                <div className="va-field">
                  <label className="va-field__label">E-mail <sup>*</sup></label>
                  <input className="va-input" type="email" value={form.email} onChange={setField('email')} />
                  <span className="va-field__hint">Le billet et les notifications de trafic vous seront envoyés à cette adresse.</span>
                </div>
              </div>
            </div>
            <div className="va-banner">
              <span className="va-banner__icon"><IShield size={16} /></span>
              <span>
                <strong>Vos données restent privées.</strong> Aucun compte requis, l&rsquo;assistant
                vérifiera votre identité à chaque accès au billet.
              </span>
            </div>
          </div>
        </div>

        <div>
          <div className="va-summary">
            <div className="va-summary__head">
              <div className="va-summary__title">Récapitulatif</div>
              <div style={{ fontSize: 13, color: 'var(--va-text-muted)' }}>{r.company} · {r.depart} → {r.arrive}</div>
            </div>
            <div className="va-summary__rows">
              <div className="va-summary__row" style={{ borderBottom: '1px dashed var(--va-border)', paddingBottom: 8, marginBottom: 4 }}>
                <span>Type de trajet</span>
                <strong>{tripTypeLabel(tripType)}{isRoundTrip(tripType) ? ' (×2)' : ''}</strong>
              </div>
              {isRoundTrip(tripType) && dateRetour && (
                <div className="va-summary__row va-summary__row--muted">
                  <span>Retour prévu</span><strong>{dateRetour}</strong>
                </div>
              )}
              <div className="va-summary__row" style={{ borderBottom: '1px dashed var(--va-border)', paddingBottom: 8, marginBottom: 4 }}>
                <span>Classe</span><strong>{totals.cls.label}</strong>
              </div>
              {pax.adultes > 0 && (
                <div className="va-summary__row">
                  <span>Adulte × {pax.adultes}</span>
                  <strong>{totals.adultPrice * pax.adultes} €</strong>
                </div>
              )}
              {pax.enfants > 0 && (
                <div className="va-summary__row">
                  <span>Enfant × {pax.enfants} <small style={{ color: 'var(--va-text-muted)' }}>(−50 %)</small></span>
                  <strong>{totals.childPrice * pax.enfants} €</strong>
                </div>
              )}
              {pax.bebes > 0 && (
                <div className="va-summary__row">
                  <span>Bébé × {pax.bebes} <small style={{ color: 'var(--va-text-muted)' }}>{r.mode === 'plane' ? '(−90 %)' : '(gratuit)'}</small></span>
                  <strong>{totals.babyPrice * pax.bebes} €</strong>
                </div>
              )}
              {bagOpts.map((b) => (bags[b.id] || 0) > 0 && (
                <div key={b.id} className="va-summary__row">
                  <span>{b.label} × {bags[b.id]}</span>
                  <strong>{b.price * bags[b.id]} €</strong>
                </div>
              ))}
              <div className="va-summary__row"><span>Assurance annulation</span><strong>6,90 €</strong></div>
              <div className="va-summary__row va-summary__row--muted"><span>Frais de service</span><strong>0 €</strong></div>
            </div>
            <div className="va-summary__total">
              <small>Total TTC · {paxLabel(pax)}{paxBreakdown(pax) ? ` (${paxBreakdown(pax)})` : ''}</small>
              <strong>{totals.total} €</strong>
            </div>
            {error && (
              <div className="va-form__error" style={{ marginBottom: 12 }}>{error}</div>
            )}
            {!auth || !auth.isAuth ? (
              <>
                <button
                  className="va-btn va-btn--primary va-btn--lg"
                  style={{ width: '100%' }}
                  onClick={confirmAndPay}>
                  Se connecter pour réserver <IArrowRight size={16} />
                </button>
                <div style={{ fontSize: 12, color: 'var(--va-text-muted)', textAlign: 'center', marginTop: 8 }}>
                  Un compte est nécessaire pour finaliser la réservation et retrouver vos billets.
                </div>
              </>
            ) : (
              <>
                <button
                  className="va-btn va-btn--primary va-btn--lg"
                  style={{ width: '100%' }}
                  disabled={busy}
                  onClick={confirmAndPay}>
                  {busy ? 'Réservation…' : 'Confirmer et payer'} <IArrowRight size={16} />
                </button>
                {!requiredOk && (
                  <div style={{ fontSize: 12, color: 'var(--va-text-muted)', textAlign: 'center', marginTop: 8 }}>
                    Date de naissance et téléphone non remplis par Google — complétez-les ci-dessus.
                  </div>
                )}
                {requiredOk && (
                  <div style={{ fontSize: 11.5, color: 'var(--va-text-muted)', textAlign: 'center', marginTop: 6 }}>
                    Paiement sécurisé · Cartes &amp; SEPA · Sans engagement
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ──────────────────────────────────────────────────────────
   CONFIRMATION
   ──────────────────────────────────────────────────────── */
const genTicketNum = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  const nums = '23456789';
  const pick = (set, n) => Array.from({ length: n }, () => set[Math.floor(Math.random() * set.length)]).join('');
  return `TRV-2026-${pick(chars, 2)}${pick(nums, 2)}${pick(chars, 1)}${pick(nums, 1)}`;
};

const ConfirmPage = ({ go, ctx }) => {
  const r = ctx && ctx.route;
  const f = (ctx && ctx.form) || {};
  const totals = (ctx && ctx.totals) || (r ? { total: r.price, cls: { label: r.class || 'Standard' } } : { total: 0, cls: { label: 'Standard' } });
  if (!r) { React.useEffect(() => go('home'), []); return null; }
  const [num] = React.useState(() => (ctx && ctx.ticketNum) || genTicketNum());
  const Icon = MODE_ICONS[r.mode] || ITrain;
  return (
    <div className="va-anim-in">
      <div className="va-confirm">
        <div className="va-confirm__seal">
          <ICheck size={28} strokeWidth={2.4} />
        </div>
        <h1 className="va-confirm__title">
          Bon voyage, {f.prenom}.<br />
          Votre billet est <em>confirmé.</em>
        </h1>
        <div className="va-confirm__sub">
          Nous venons d&rsquo;envoyer votre billet à <strong style={{ color: 'var(--va-text)' }}>{f.email}</strong>.
          Vous pourrez le retrouver à tout moment depuis « Mes billets » ou en demandant à l&rsquo;assistant.
        </div>

        <div className="va-bigticket">
          <div className="va-bigticket__head">
            <div className="va-bigticket__num">
              <small>Numéro de billet</small>
              <strong>{num}</strong>
            </div>
            <div className="va-bigticket__brand">
              <span className="va-bigticket__brand__logo"><Icon size={16} /></span>
              <span>{r.company}<br /><span style={{ color: 'var(--va-text-muted)', fontWeight: 400 }}>{r.class}</span></span>
            </div>
          </div>
          <div className="va-bigticket__body">
            <div className="va-bigticket__route">
              <div className="va-detailroute">
                <div className="va-detailroute__stop">
                  <div className="va-detailroute__time">{r.depart}</div>
                  <div className="va-detailroute__date">Sam. 13 juin 2026</div>
                  <div className="va-detailroute__city">{r.from}</div>
                </div>
                <div className="va-detailroute__sep">
                  <div>{r.dur}</div>
                  <div className="va-detailroute__sep-line"><StopDots stops={r.stops} /></div>
                  <div style={{ color: r.escales && r.escales.length > 0 ? 'var(--va-accent)' : undefined }}>{r.stops}</div>
                  {r.escales && r.escales.length > 0 && <div style={{ fontSize: 10, color: 'var(--va-text-muted)' }}>via {r.escales.join(' · ')}</div>}
                </div>
                <div className="va-detailroute__stop va-detailroute__stop--right">
                  <div className="va-detailroute__time">{r.arrive}</div>
                  <div className="va-detailroute__date">Sam. 13 juin 2026</div>
                  <div className="va-detailroute__city">{r.to}</div>
                </div>
              </div>
            </div>
            <div className="va-bigticket__qrwrap">
              <div className="va-bigticket__qr"><QRCode seed={num} size={120} /></div>
              <div className="va-bigticket__qrlabel">À présenter à l&rsquo;embarquement</div>
            </div>
          </div>
          <div className="va-bigticket__foot">
            <div>
              <span className="va-bigticket__foot__label">Voyageur</span>
              <span className="va-bigticket__foot__value">{f.prenom} {f.nom}</span>
            </div>
            <div>
              <span className="va-bigticket__foot__label">Voiture / Siège</span>
              <span className="va-bigticket__foot__value">{r.mode === 'plane' ? '24 A' : 'V.7 · 23 F'}</span>
            </div>
            <div>
              <span className="va-bigticket__foot__label">Tarif</span>
              <span className="va-bigticket__foot__value">{totals.cls.label}</span>
            </div>
            <div>
              <span className="va-bigticket__foot__label">Total payé</span>
              <span className="va-bigticket__foot__value">{totals.total} €</span>
            </div>
          </div>
        </div>

        <div className="va-confirm__cta">
          <button className="va-btn va-btn--primary va-btn--lg" onClick={() => go('mes-billets')}>
            <IFile size={16} /> Voir mes billets
          </button>
          <button className="va-btn va-btn--secondary va-btn--lg" onClick={() => go('assistant')}>
            <IMessage size={16} /> Parler à l&rsquo;assistant
          </button>
        </div>

        <div className="va-confirm__meta">
          <ICheckCircle size={14} style={{ color: 'var(--va-success)' }} />
          E-mail envoyé · paiement débité (CB Visa •• 4218) · billet rétractable jusqu&rsquo;à J–1
        </div>
      </div>
    </div>
  );
};

/* ──────────────────────────────────────────────────────────
   MES BILLETS (number entry + verification flow)
   ──────────────────────────────────────────────────────── */
const MesBilletsPage = ({ go, ctx, auth }) => {
  const [step, setStep] = React.useState('enter'); // enter → verify → done
  const [num, setNum] = React.useState('');
  const [id, setId] = React.useState({ nom: '', prenom: '', dob: '' });
  const [verifying, setVerifying] = React.useState(false);
  const [verifyError, setVerifyError] = React.useState('');
  const setField = (k) => (e) => setId((s) => ({ ...s, [k]: e.target.value }));
  const validNum = /^TRV-2026-[A-Z0-9]{6,}$/.test(num.trim().toUpperCase());

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyError('');
    try {
      const res = await fetch(`${window.VA_CONFIG.API_BASE}/billets/access`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numero_billet: num.trim().toUpperCase(),
          identity: { nom: id.nom, prenom: id.prenom, date_naissance: id.dob },
        }),
      });
      if (!res.ok) { setVerifyError('Numéro de billet ou identité incorrects.'); return; }
      const billet = await res.json();
      const t = billet.trajet || {};
      const dep = t.date_depart ? new Date(t.date_depart) : null;
      const arr = t.date_arrivee ? new Date(t.date_arrivee) : null;
      const hh = (d) => d ? `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` : '';
      const modeKey = { avion: 'plane', train: 'train', bateau: 'ship', bus: 'bus' }[t.type] || 'train';
      const route = {
        id: t.id, mode: modeKey,
        company: t.compagnie || '', class: billet.tarif || 'Standard',
        depart: hh(dep), arrive: hh(arr),
        from: t.depart || '', to: t.arrivee || '',
        price: billet.prix_paye || 0,
        stops: t.stops || 'direct',
      };
      go('confirm', {
        ticketNum: billet.numero_billet,
        form: { nom: billet.user?.nom || id.nom, prenom: billet.user?.prenom || id.prenom, email: billet.user?.email || '' },
        route,
        totals: { total: billet.prix_paye, cls: { label: billet.tarif || 'Standard' } },
      });
    } catch { setVerifyError('Erreur de connexion au serveur.'); }
    finally { setVerifying(false); }
  };

  // Si l'utilisateur est connecté : on charge directement ses billets
  const isAuth = !!(auth && auth.isAuth);
  const [myBillets, setMyBillets] = React.useState(null);
  const [loadingBillets, setLoadingBillets] = React.useState(false);

  React.useEffect(() => {
    if (!isAuth) { setMyBillets(null); return; }
    setLoadingBillets(true);
    window.VA_API.myBillets()
      .then((data) => setMyBillets(data || []))
      .catch(() => setMyBillets([]))
      .finally(() => setLoadingBillets(false));
  }, [isAuth, auth && auth.user && auth.user.id]);

  if (isAuth) {
    return (
      <div className="va-anim-in">
        <div className="va-pagehead">
          <div className="va-pagehead__top">
            <div className="va-crumb">
              <a onClick={() => go('home')}>Accueil</a>
              <span className="va-crumb__sep">/</span>
              <span className="va-crumb__current">Mes billets</span>
            </div>
          </div>
          <h1 className="va-pagehead__title">Historique de mes billets</h1>
          <div className="va-pagehead__sub">
            Retrouvez ici tous les billets achetés avec ce compte ({auth.user.email}).
          </div>
        </div>

        <div
          className="va-mestickets"
          style={{
            maxWidth: 880, margin: '0 auto',
            minHeight: 'auto', display: 'block',
            padding: '24px 24px 64px',
          }}
        >
          {loadingBillets && (
            <div style={{ padding: 28, textAlign: 'center', color: 'var(--va-text-muted)' }}>Chargement…</div>
          )}
          {!loadingBillets && myBillets && myBillets.length === 0 && (
            <div className="va-mestickets__card" style={{ textAlign: 'center' }}>
              <div className="va-mestickets__icon" style={{ margin: '0 auto 12px' }}><IFile size={22} /></div>
              <div className="va-mestickets__title">Aucun billet pour l’instant</div>
              <div className="va-mestickets__sub" style={{ marginBottom: 18 }}>
                Vos prochaines réservations apparaîtront ici automatiquement.
              </div>
              <button className="va-btn va-btn--primary" onClick={() => go('home')}>
                Faire une recherche <IArrowRight size={16} />
              </button>
            </div>
          )}
          {!loadingBillets && myBillets && myBillets.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {myBillets.map((b) => {
                const t = b.trajet || {};
                const dDep = t.date_depart ? new Date(t.date_depart) : null;
                const Icon = (t.type === 'avion' ? IPlane : t.type === 'bus' ? IBus : t.type === 'bateau' ? IShip : ITrain);
                const isFuture = dDep && dDep > new Date();
                return (
                  <div
                    key={b.id}
                    style={{
                      background: 'var(--va-surface)', border: '1px solid var(--va-border)',
                      borderRadius: 14, padding: 18,
                      display: 'grid', gridTemplateColumns: '40px 1fr auto', gap: 16, alignItems: 'center',
                    }}
                  >
                    <div style={{
                      width: 40, height: 40, borderRadius: 10,
                      background: 'rgba(217, 119, 87, 0.1)', color: 'var(--va-accent)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Icon size={20} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                        <strong style={{ fontSize: 15, color: 'var(--va-text)' }}>{t.depart} → {t.arrivee}</strong>
                        <span style={{
                          fontSize: 11, padding: '2px 8px', borderRadius: 999, fontWeight: 600,
                          background: b.statut === 'annule' ? 'rgba(255, 80, 80, 0.12)' : isFuture ? 'rgba(56, 142, 60, 0.12)' : 'var(--va-surface-2)',
                          color: b.statut === 'annule' ? '#c62828' : isFuture ? '#2e7d32' : 'var(--va-text-muted)',
                          border: '1px solid transparent',
                        }}>
                          {b.statut === 'annule' ? 'Annulé' : isFuture ? 'À venir' : 'Terminé'}
                        </span>
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--va-text-muted)', marginTop: 4 }}>
                        {t.compagnie || '—'} · {t.classe || 'Standard'}
                        {dDep && <> · {dDep.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })} à {dDep.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</>}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--va-text-subtle, var(--va-text-muted))', marginTop: 4, fontFamily: 'JetBrains Mono, ui-monospace, monospace' }}>
                        {b.numero_billet}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--va-text)' }}>{Math.round(b.prix_paye)} €</div>
                      <button
                        type="button"
                        className="va-btn va-btn--sm va-btn--secondary"
                        style={{ marginTop: 6 }}
                        onClick={() => go('confirm', { ticketNum: b.numero_billet, form: { nom: b.user.nom, prenom: b.user.prenom, email: b.user.email }, route: { mode: t.type === 'avion' ? 'plane' : t.type === 'bus' ? 'bus' : t.type === 'bateau' ? 'ship' : 'train', company: t.compagnie, class: t.classe, depart: dDep ? dDep.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '', arrive: '', from: t.depart, to: t.arrivee, dur: '', stops: '', price: Math.round(b.prix_paye) }, totals: { total: Math.round(b.prix_paye), cls: { label: t.classe || 'Standard' } } })}
                      >
                        Voir le billet
                      </button>
                    </div>
                  </div>
                );
              })}
              <div style={{ textAlign: 'center', marginTop: 6 }}>
                <button className="va-btn va-btn--ghost" onClick={() => go('home')}>
                  <IArrowLeft size={14} /> Retour à l’accueil
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="va-anim-in">
      <div className="va-pagehead">
        <div className="va-pagehead__top">
          <div className="va-crumb">
            <a onClick={() => go('home')}>Accueil</a>
            <span className="va-crumb__sep">/</span>
            <span className="va-crumb__current">Mes billets</span>
          </div>
        </div>
        <h1 className="va-pagehead__title">Accéder à un billet</h1>
        <div className="va-pagehead__sub">Aucune création de compte requise — votre numéro et une vérification d&rsquo;identité suffisent.</div>
      </div>

      <div className="va-mestickets">
        <div className="va-mestickets__card">
          <div className="va-mestickets__head">
            <div className="va-mestickets__icon">{step === 'enter' ? <IFile size={22} /> : <IShield size={22} />}</div>
            <div className="va-mestickets__title">
              {step === 'enter' ? 'Votre numéro de billet' :
               step === 'verify' ? 'Vérifions votre identité' : 'Identité vérifiée'}
            </div>
            <div className="va-mestickets__sub">
              {step === 'enter'
                ? 'Le numéro figure dans l\u2019e-mail de confirmation, format TRV-2026-XXXXXX.'
                : step === 'verify'
                ? 'Confirmez les informations du voyageur principal pour accéder au billet.'
                : 'Votre billet est en cours de chargement…'}
            </div>
          </div>

          {step === 'enter' && (
            <div className="va-form">
              <div className="va-field">
                <label className="va-field__label">Numéro de billet</label>
                <div className="va-input-wrap">
                  <span className="va-input-wrap__icon"><IFile size={16} /></span>
                  <input
                    className="va-input va-input--with-icon"
                    value={num}
                    onChange={(e) => setNum(e.target.value.toUpperCase())}
                    placeholder="TRV-2026-XXXXXX"
                    style={{ fontFamily: 'JetBrains Mono, ui-monospace, monospace', letterSpacing: '0.04em' }}
                  />
                </div>
                <span className="va-field__hint">Vous avez perdu votre numéro&nbsp;? <a style={{ color: 'var(--va-accent)', fontWeight: 500, cursor: 'pointer' }} onClick={() => go('assistant')}>Demandez à l&rsquo;assistant.</a></span>
              </div>
              <button
                className="va-btn va-btn--primary va-btn--lg"
                style={{ width: '100%' }}
                disabled={!validNum}
                onClick={() => setStep('verify')}>
                Continuer <IArrowRight size={16} />
              </button>
            </div>
          )}

          {step === 'verify' && (
            <div className="va-form">
              <div className="va-form__row">
                <div className="va-field">
                  <label className="va-field__label">Nom</label>
                  <input className="va-input" value={id.nom} onChange={setField('nom')} placeholder="Moreau" />
                </div>
                <div className="va-field">
                  <label className="va-field__label">Prénom</label>
                  <input className="va-input" value={id.prenom} onChange={setField('prenom')} placeholder="Camille" />
                </div>
              </div>
              <div className="va-field">
                <label className="va-field__label">Date de naissance</label>
                <div className="va-input-wrap">
                  <span className="va-input-wrap__icon"><ICalendar size={16} /></span>
                  <input className="va-input va-input--with-icon" value={id.dob} onChange={setField('dob')} placeholder="JJ/MM/AAAA" />
                </div>
              </div>
              {verifyError && (
                <div style={{ padding: '8px 12px', background: '#fff0f0', border: '1px solid #e53e3e', borderRadius: 8, fontSize: 13, color: '#e53e3e' }}>
                  {verifyError}
                </div>
              )}
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="va-btn va-btn--ghost" style={{ flex: '0 0 auto' }} onClick={() => setStep('enter')}>
                  <IArrowLeft size={16} /> Retour
                </button>
                <button
                  className="va-btn va-btn--primary"
                  style={{ flex: 1 }}
                  disabled={!(id.nom && id.prenom && id.dob) || verifying}
                  onClick={handleVerify}>
                  {verifying ? 'Vérification…' : <><IShield size={16} /> Accéder à mon billet</>}
                </button>
              </div>
            </div>
          )}

          <div className="va-mestickets__alt">
            Pas encore de billet&nbsp;? <a onClick={() => go('home')}>Faire une recherche</a>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, {
  HomePage, ResultsPage, BookingPage, ConfirmPage, MesBilletsPage,
});
