/* Voyage Assistant — shared UI pieces.
   Wordmark, Nav, ThemeToggle, SearchBar, ModeCards, DestinationGrid, FAB.
   All assume the icon globals from voyage-icons.jsx are loaded. */

const Wordmark = ({ size = 'md' }) => {
  const fz = size === 'lg' ? 19 : size === 'sm' ? 14 : 17;
  return (
    <div className="va-mark" style={{ fontSize: fz }}>
      <span className="va-mark__dot"></span>
      <span className="va-mark__type">
        Voyage<em>· assistant</em>
      </span>
    </div>
  );
};

const ThemeToggle = ({ active = 'light' }) => (
  <div className="va-themetoggle" aria-label="Thème">
    <button className={active === 'light' ? 'is-active' : ''} title="Clair"><ISun size={14} /></button>
    <button className={active === 'dark' ? 'is-active' : ''} title="Sombre"><IMoon size={14} /></button>
    <button className={active === 'system' ? 'is-active' : ''} title="Système"><IMonitor size={14} /></button>
  </div>
);

const Nav = ({ bordered = false, theme = 'light' }) => (
  <nav className={`va-nav ${bordered ? 'va-nav--bordered' : ''}`}>
    <Wordmark />
    <div className="va-nav__links">
      <a>Destinations</a>
      <a>Mes billets</a>
      <a>Assistant</a>
      <a>Aide</a>
    </div>
    <div className="va-nav__right">
      <button className="va-iconbtn" title="Langue"><IGlobe size={18} /></button>
      <ThemeToggle active={theme} />
      <button className="va-btn va-btn--sm va-btn--secondary" style={{ marginLeft: 6 }}>Se connecter</button>
    </div>
  </nav>
);

const SearchBar = ({ values, compact = false }) => {
  const v = values || {
    from: { city: 'Paris', code: 'CDG · Gare de Lyon' },
    to: { city: 'Marseille', code: 'MRS · Saint-Charles' },
    date: { label: 'Sam. 13 juin', sub: '1 trajet' },
    pax: { label: '2 voyageurs', sub: '1 adulte · 1 enfant' },
  };
  return (
    <div className="va-search">
      <div className="va-search__field">
        <span className="va-search__label">Départ</span>
        <span className="va-search__value">
          <IMapPin size={16} style={{ color: 'var(--va-text-muted)' }} />
          {v.from.city}
        </span>
        {!compact && <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{v.from.code}</span>}
      </div>
      <button className="va-search__swap" title="Inverser"><ISwap size={15} /></button>
      <div className="va-search__field">
        <span className="va-search__label">Arrivée</span>
        <span className="va-search__value">
          <IMapPin size={16} style={{ color: 'var(--va-text-muted)' }} />
          {v.to.city}
        </span>
        {!compact && <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{v.to.code}</span>}
      </div>
      <div className="va-search__field">
        <span className="va-search__label">Date</span>
        <span className="va-search__value">
          <ICalendar size={16} style={{ color: 'var(--va-text-muted)' }} />
          {v.date.label}
        </span>
        {!compact && <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{v.date.sub}</span>}
      </div>
      <div className="va-search__field">
        <span className="va-search__label">Voyageurs</span>
        <span className="va-search__value">
          <IUsers size={16} style={{ color: 'var(--va-text-muted)' }} />
          {v.pax.label}
        </span>
        {!compact && <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{v.pax.sub}</span>}
      </div>
      <button className="va-search__cta">
        <ISearch size={16} />
        Rechercher
      </button>
    </div>
  );
};

const MODES = [
  { key: 'plane', label: 'Avion',  sub: '450+ compagnies · 159 000 routes', meta: 'dès 49 €', Icon: IPlane },
  { key: 'train', label: 'Train',  sub: 'SNCF · Eurostar · DB · Trenitalia · Renfe', meta: 'dès 19 €', Icon: ITrain },
  { key: 'ship',  label: 'Bateau', sub: 'P&O · Brittany Ferries · Corsica Linea…', meta: 'dès 19 €', Icon: IShip },
  { key: 'bus',   label: 'Bus',    sub: 'FlixBus · BlaBlaBus · liaisons EU', meta: 'dès 5 €', Icon: IBus },
];

const ModeCards = ({ active = 'train' }) => (
  <div className="va-modes">
    {MODES.map(({ key, label, sub, meta, Icon }) => (
      <button key={key} className={`va-mode ${active === key ? 'is-active' : ''}`}>
        <div className="va-mode__icon"><Icon size={22} /></div>
        <div>
          <div className="va-mode__label">{label}</div>
          <div className="va-mode__sub">{sub}</div>
        </div>
        <div className="va-mode__meta">
          <span>{meta}</span>
          <IChevronRight size={14} style={{ color: 'var(--va-text-subtle)' }} />
        </div>
      </button>
    ))}
  </div>
);

const ModeTabs = ({ active = 'all', onSelect }) => (
  <div className="va-modetabs">
    <button
      type="button"
      className={active === 'all' ? 'is-active' : ''}
      onClick={(e) => { e.stopPropagation(); onSelect && onSelect('all'); }}
    >
      <ISearch size={16} />
      Tous
    </button>
    {MODES.map(({ key, label, Icon }) => (
      <button
        key={key}
        type="button"
        className={active === key ? 'is-active' : ''}
        onClick={(e) => { e.stopPropagation(); onSelect && onSelect(key); }}
      >
        <Icon size={16} />
        {key === 'bus' ? 'Bus' : label}
      </button>
    ))}
  </div>
);

const MODE_KEY_TO_API = { all: null, plane: 'avion', train: 'train', ship: 'bateau', bus: 'bus' };
const MODE_API_TO_KEY = { avion: 'plane', train: 'train', bateau: 'ship', bus: 'bus' };


const DestinationImg = ({ city, src }) => {
  const fallback = `https://picsum.photos/seed/${encodeURIComponent(city)}/600/400`;
  const [url, setUrl] = React.useState(src || fallback);
  React.useEffect(() => { setUrl(src || fallback); }, [src]);
  return (
    <div
      className="va-dest__img"
      style={{ backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
    >
      <img src={url} alt="" style={{ display: 'none' }} onError={() => setUrl(fallback)} />
    </div>
  );
};

/* Carousel dynamique — charge les destinations depuis le backend */
const DestinationsCarousel = ({ perPage = 4, onPick, depart = 'Paris' }) => {
  const [destinations, setDestinations] = React.useState([]);
  const [images, setImages] = React.useState({});
  const [page, setPage] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

  // Charge les destinations réelles depuis le backend
  React.useEffect(() => {
    setLoading(true);
    fetch(`${window.VA_CONFIG.API_BASE}/trajets/destinations?depart=${encodeURIComponent(depart)}&limit=24`)
      .then(r => r.json())
      .then(data => {
        setDestinations(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        setDestinations([]);
        setLoading(false);
      });
  }, [depart]);

  // Charge les images Pixabay pour les destinations visibles
  React.useEffect(() => {
    if (!destinations.length) return;
    const start = page * perPage;
    const visible = destinations.slice(start, start + perPage);
    visible.forEach(d => {
      if (images[d.ville]) return;
      fetch(`${window.VA_CONFIG.API_BASE}/images?q=${encodeURIComponent(d.ville + ' city travel')}&mode=ville`)
        .then(r => r.json())
        .then(data => {
          if (data.url) setImages(prev => ({ ...prev, [d.ville]: data.url }));
        })
        .catch(() => {});
    });
  }, [page, destinations]);

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--va-text-muted)' }}>Chargement des destinations…</div>
  );

  if (!destinations.length) return null;

  const pages = Math.ceil(destinations.length / perPage);
  const visible = destinations.slice(page * perPage, page * perPage + perPage);

  return (
    <div>
      <div className="va-destgrid">
        {visible.map((d, i) => (
          <button
            key={`${d.ville}-${page}-${i}`}
            type="button"
            className="va-dest"
            onClick={() => onPick && onPick({ city: d.ville, country: d.pays || '', price: `dès ${d.prix_min} €` })}
            style={{ border: 'none', background: 'transparent', padding: 0, textAlign: 'left', cursor: 'pointer', fontFamily: 'inherit' }}
          >
            <DestinationImg city={d.ville} src={d.img || images[d.ville] || null} />
            <div className="va-dest__body">
              <div>
                <div className="va-dest__city">{d.ville}</div>
                <div className="va-dest__country">{d.pays || ''}</div>
              </div>
              <span className="va-dest__price">dès {d.prix_min} €</span>
            </div>
          </button>
        ))}
      </div>
      {pages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 28 }}>
          <button type="button" className="va-iconbtn" onClick={() => setPage((p) => (p - 1 + pages) % pages)} aria-label="Précédent" style={{ transform: 'rotate(180deg)' }}>
            <IChevronRight size={16} />
          </button>
          {Array.from({ length: pages }).map((_, i) => (
            <button key={i} type="button" onClick={() => setPage(i)}
              style={{ width: 30, height: 30, borderRadius: 999, border: i === page ? '1px solid var(--va-text)' : '1px solid var(--va-border)', background: i === page ? 'var(--va-text)' : 'transparent', color: i === page ? 'var(--va-bg)' : 'var(--va-text-muted)', fontFamily: 'inherit', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
              {i + 1}
            </button>
          ))}
          <button type="button" className="va-iconbtn" onClick={() => setPage((p) => (p + 1) % pages)} aria-label="Suivant">
            <IChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};

const FAB = ({ label = 'Discuter avec l\u2019assistant' }) => (
  <button className="va-fab">
    <span className="va-fab__avatar"><ISparkles size={16} /></span>
    {label}
  </button>
);

/* Section: "Pourquoi Voyage" — value props row */
const ValueProps = () => (
  <div style={{
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 4,
    background: 'var(--va-surface-2)', border: '1px solid var(--va-border)',
    borderRadius: 'var(--va-radius-lg)', padding: 4,
  }}>
    {[
      { Icon: ICheck,    title: 'Un seul billet',     sub: 'Multi-mode, multi-compagnies' },
      { Icon: IShield,   title: 'Garantie 0 stress',  sub: 'Remboursement en 48 h' },
      { Icon: ISparkles, title: 'Assistant 24 / 7',   sub: 'Retards, modifications, réclas' },
      { Icon: IGlobe,    title: '3 000 destinations', sub: 'Europe, Afrique, Amériques, Asie' },
    ].map(({ Icon, title, sub }, i) => (
      <div key={i} style={{
        display: 'flex', alignItems: 'flex-start', gap: 12,
        padding: '18px 20px', background: 'var(--va-bg)', borderRadius: 'var(--va-radius-md)',
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, background: 'var(--va-surface-2)',
          color: 'var(--va-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}><Icon size={16} /></div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--va-text)', letterSpacing: '-0.005em' }}>{title}</div>
          <div style={{ fontSize: 12, color: 'var(--va-text-muted)', marginTop: 2 }}>{sub}</div>
        </div>
      </div>
    ))}
  </div>
);

/* ──────────────────────────────────────────────────────────
   PRICING — pax / classes / bagages (style booking.com / Air France)
   ──────────────────────────────────────────────────────── */

const CLASS_OPTIONS = {
  plane: [
    { id: 'eco',      label: 'Économique',     sub: 'Le tarif de base',                    mult: 1.0 },
    { id: 'premium',  label: 'Premium éco',    sub: 'Plus d’espace, repas chaud',          mult: 1.4 },
    { id: 'business', label: 'Affaires',       sub: 'Siège-lit, salon, prioritaire',       mult: 2.2 },
    { id: 'first',    label: 'Première',       sub: 'Suite privée, service dédié',         mult: 3.0 },
  ],
  train: [
    { id: 'eco',     label: '2ⁿᵈᵉ classe',   sub: 'Confort standard',                     mult: 1.0 },
    { id: 'premium', label: '1ʳᵉ classe',    sub: 'Plus large, prise individuelle',       mult: 1.5 },
  ],
  bus: [
    { id: 'eco',     label: 'Standard',      sub: 'Siège inclinable, Wi-Fi',              mult: 1.0 },
    { id: 'premium', label: 'Premium',       sub: 'Plus d’espace, prise USB',             mult: 1.3 },
  ],
  ship: [
    { id: 'eco',      label: 'Pont',                sub: 'Fauteuil sur le pont',          mult: 1.0 },
    { id: 'premium',  label: 'Cabine intérieure',   sub: '2 à 4 couchettes',              mult: 1.6 },
    { id: 'business', label: 'Cabine extérieure',   sub: 'Hublot ou balcon privatif',     mult: 2.2 },
  ],
};

const BAG_OPTIONS = {
  plane: [
    { id: 'cabin_8',  label: 'Bagage cabine 8 kg',        sub: '55 × 40 × 20 cm',  price: 15 },
    { id: 'hold_23',  label: 'Bagage en soute 23 kg',     sub: '158 cm cumulés',   price: 30 },
    { id: 'hold_32',  label: 'Bagage en soute 32 kg',     sub: '158 cm cumulés',   price: 55 },
  ],
  bus:   [{ id: 'big_bag', label: 'Grande valise en soute', sub: '80 × 50 × 30 cm', price: 10 }],
  train: [],
  ship:  [],
};

const BAG_INCLUDED_LABEL = 'Sac à dos cabine inclus · 40 × 20 × 25 cm (~7 kg)';

const _CLASS_LABEL_MAP = {
  // avion
  'économique': 'eco', 'eco': 'eco', 'standard': 'eco',
  'premium economy': 'premium', 'premium éco': 'premium', 'premium': 'premium',
  'business': 'business', 'affaires': 'business',
  'première': 'first', 'first': 'first', 'first class': 'first',
  // train
  '2nde · loisir': 'eco', '2nde · pro': 'eco', '2nde': 'eco',
  '1ère · pro': 'premium', '1ère': 'premium',
  // bateau
  'pont': 'eco',
  'cabine 2': 'premium', 'cabine 4': 'premium', 'cabine intérieure': 'premium',
  'cabine premium': 'business', 'cabine extérieure': 'business',
  // bus
};
const guessClassId = (classeLabel, mode) => {
  if (!classeLabel) return null;
  const key = classeLabel.toLowerCase().trim();
  const guessed = _CLASS_LABEL_MAP[key] || null;
  const opts = CLASS_OPTIONS[mode] || CLASS_OPTIONS.train;
  if (guessed && opts.find(o => o.id === guessed)) return guessed;
  return null;
};

/* Normalise les voyageurs : accepte ancien format (passagers: number) ou nouveau (pax: {adultes,enfants,bebes}) */
const normalizePax = (s) => {
  if (s && s.pax && typeof s.pax === 'object') {
    return {
      adultes: Math.max(1, s.pax.adultes || 0),
      enfants: Math.max(0, s.pax.enfants || 0),
      bebes:   Math.max(0, s.pax.bebes   || 0),
    };
  }
  const n = (s && typeof s.passagers === 'number') ? s.passagers : 1;
  return { adultes: Math.max(1, n), enfants: 0, bebes: 0 };
};
const paxCount = (p) => (p.adultes || 0) + (p.enfants || 0) + (p.bebes || 0);
const paxLabel = (p) => {
  const t = paxCount(p);
  return `${t} voyageur${t > 1 ? 's' : ''}`;
};
const paxBreakdown = (p) => {
  const parts = [];
  if (p.adultes) parts.push(`${p.adultes} adulte${p.adultes > 1 ? 's' : ''}`);
  if (p.enfants) parts.push(`${p.enfants} enfant${p.enfants > 1 ? 's' : ''}`);
  if (p.bebes)   parts.push(`${p.bebes} bébé${p.bebes > 1 ? 's' : ''}`);
  return parts.join(' · ');
};

const computeBookingTotal = ({ basePrice, mode, pax, classId, bags, tripType }) => {
  const classes = CLASS_OPTIONS[mode] || CLASS_OPTIONS.train;
  const cls = classes.find(c => c.id === classId) || classes[0];
  const tripMult   = isRoundTrip(tripType) ? 2 : 1;
  const adultPrice = basePrice * cls.mult * tripMult;
  const childPrice = adultPrice * 0.5;
  const babyPrice  = mode === 'plane' ? adultPrice * 0.1 : 0;
  const bagOpts    = BAG_OPTIONS[mode] || [];
  // Bagages : compte aller + retour si aller-retour (chaque trajet a son lot)
  const bagsTotal  = bagOpts.reduce((s, b) => s + (((bags && bags[b.id]) || 0) * b.price * tripMult), 0);
  const paxTotal   = adultPrice * pax.adultes + childPrice * pax.enfants + babyPrice * pax.bebes;
  const insurance  = 6.9;
  return {
    cls,
    tripMult,
    adultPrice: Math.round(adultPrice),
    childPrice: Math.round(childPrice),
    babyPrice:  Math.round(babyPrice),
    paxTotal:   Math.round(paxTotal),
    bagsTotal:  Math.round(bagsTotal),
    insurance,
    total:      Math.round(paxTotal + bagsTotal + insurance),
  };
};

/* TripTypeTabs — 3 pills : Aller simple / Retour seul / Aller-retour */
const TRIP_TYPES = [
  { id: 'aller',        label: 'Aller simple' },
  { id: 'retour',       label: 'Retour seul' },
  { id: 'aller_retour', label: 'Aller-retour' },
];

const TripTypeTabs = ({ value, onChange }) => (
  <div style={{ display: 'inline-flex', gap: 4, padding: 4, borderRadius: 999, background: 'var(--va-surface-2)', border: '1px solid var(--va-border)' }}>
    {TRIP_TYPES.map((t) => {
      const sel = (value || 'aller') === t.id;
      return (
        <button
          key={t.id}
          type="button"
          onClick={() => onChange(t.id)}
          style={{
            padding: '6px 14px', borderRadius: 999, fontSize: 13, fontWeight: 600,
            border: 'none', cursor: 'pointer', fontFamily: 'inherit',
            background: sel ? 'var(--va-accent)' : 'transparent',
            color: sel ? '#fff' : 'var(--va-text-muted)',
            transition: 'all 120ms ease',
          }}
        >{t.label}</button>
      );
    })}
  </div>
);

const tripTypeLabel = (t) => (TRIP_TYPES.find(x => x.id === t) || TRIP_TYPES[0]).label;
const isRoundTrip = (t) => t === 'aller_retour';

/* PaxStepper — popover avec +/- pour adultes / enfants / bébés */
const StepBtn = ({ onClick, disabled, children }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    style={{
      width: 30, height: 30, borderRadius: '50%',
      border: '1px solid var(--va-border)',
      background: disabled ? 'var(--va-surface-2)' : 'var(--va-surface)',
      color: disabled ? 'var(--va-text-muted)' : 'var(--va-text)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontSize: 16, fontFamily: 'inherit', lineHeight: 1,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    }}
  >{children}</button>
);

const PaxStepper = ({ value, onChange, onValidate }) => {
  const pax = normalizePax({ pax: value });
  const set = (k, v) => onChange({ ...pax, [k]: Math.max(0, v) });
  const seats = (pax.adultes || 0) + (pax.enfants || 0);
  const Row = ({ label, sub, k, min = 0, capByseats = false }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0' }}>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--va-text)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{sub}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <StepBtn onClick={() => set(k, pax[k] - 1)} disabled={pax[k] <= min}>−</StepBtn>
        <span style={{ minWidth: 18, textAlign: 'center', fontWeight: 600, color: 'var(--va-text)' }}>{pax[k]}</span>
        <StepBtn onClick={() => set(k, pax[k] + 1)} disabled={capByseats ? false : seats >= 9}>+</StepBtn>
      </div>
    </div>
  );
  return (
    <div style={{
      padding: 16, minWidth: 280, background: 'var(--va-surface)',
      border: '1px solid var(--va-border)', borderRadius: 12,
      boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
    }}>
      <Row label="Adultes" sub="12 ans et plus" k="adultes" min={1} />
      <div style={{ borderTop: '1px solid var(--va-border)' }} />
      <Row label="Enfants" sub="2 à 11 ans · −50 %" k="enfants" />
      <div style={{ borderTop: '1px solid var(--va-border)' }} />
      <Row label="Bébés" sub="0 à 2 ans · gratuit (avion : −90 %)" k="bebes" capByseats />
      {onValidate && (
        <button
          type="button"
          className="va-btn va-btn--primary"
          style={{ width: '100%', marginTop: 12 }}
          onClick={onValidate}
        >OK</button>
      )}
    </div>
  );
};

Object.assign(window, {
  Wordmark, ThemeToggle, Nav,
  SearchBar, MODES, ModeCards, ModeTabs,
  DestinationGrid, DestinationsCarousel, FAB, ValueProps,
  MODE_KEY_TO_API, MODE_API_TO_KEY,
  CLASS_OPTIONS, BAG_OPTIONS, BAG_INCLUDED_LABEL, guessClassId,
  normalizePax, paxCount, paxLabel, paxBreakdown,
  computeBookingTotal, PaxStepper, StepBtn,
  TRIP_TYPES, TripTypeTabs, tripTypeLabel, isRoundTrip,
});
