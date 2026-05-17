/* Voyage Assistant — SearchBar éditable avec autocomplete lieux.
   Chaque champ est cliquable individuellement et ouvre son éditeur inline.
   Le bouton Rechercher déclenche onSearch(values). */

const Autocomplete = ({ value, onChange, onPick, placeholder, type }) => {
  const [items, setItems] = React.useState([]);
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const inputRef = React.useRef(null);
  const timerRef = React.useRef(null);

  React.useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const qs = new URLSearchParams({ q: value || '', limit: 8 });
        if (type) qs.set('type', type);
        const res = await fetch(`${window.VA_CONFIG.API_BASE}/lieux?${qs.toString()}`);
        const data = await res.json();
        setItems(Array.isArray(data) ? data : []);
      } catch { setItems([]); }
      finally { setLoading(false); }
    }, 150);
    return () => clearTimeout(timerRef.current);
  }, [value, type]);

  React.useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <input
        ref={inputRef}
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 180)}
        placeholder={placeholder}
        style={{
          width: '100%', height: 38, padding: '0 12px',
          border: '1px solid var(--va-border)', borderRadius: 8,
          fontSize: 14, fontFamily: 'inherit', color: 'var(--va-text)',
          background: 'var(--va-bg)',
        }}
      />
      {open && (items.length > 0 || loading) && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4,
          background: 'var(--va-bg)', border: '1px solid var(--va-border)',
          borderRadius: 8, zIndex: 200, maxHeight: 320, overflowY: 'auto',
          boxShadow: '0 10px 30px rgba(0,0,0,0.08)',
        }}>
          {loading && <div style={{ padding: 12, fontSize: 13, color: 'var(--va-text-muted)' }}>Recherche…</div>}
          {!loading && items.map((it, i) => (
            <button
              key={`${it.nom}-${i}`}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); onPick(it); setOpen(false); }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', padding: '10px 12px', border: 'none', background: 'transparent',
                cursor: 'pointer', textAlign: 'left', fontFamily: 'inherit',
                borderBottom: '1px solid var(--va-border-subtle, transparent)',
                color: 'var(--va-text)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--va-surface-2)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: 14, fontWeight: 500 }}>{it.nom}</span>
                <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>{it.ville} · {it.pays}</span>
              </span>
              <span style={{ fontSize: 11, color: 'var(--va-text-subtle)', fontFamily: 'monospace' }}>{it.code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const SearchBarEditable = ({ values, onChange, onSearch, type }) => {
  const [editing, setEditing] = React.useState(null); // 'depart' | 'arrivee' | 'date' | 'passagers' | null

  React.useEffect(() => {
    const onClick = (e) => {
      // Close when clicking outside the search bar
      if (!e.target.closest('.va-search')) setEditing(null);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const set = (k, v) => onChange({ ...values, [k]: v });

  const dateLabel = (() => {
    if (!values.date) return 'Choisir une date';
    const d = new Date(values.date);
    if (isNaN(d)) return 'Choisir une date';
    return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  })();

  const tripType = values.tripType || 'aller';
  const roundTrip = window.isRoundTrip(tripType);
  const retourLabel = (() => {
    if (!values.dateRetour) return 'Choisir une date';
    const d = new Date(values.dateRetour);
    if (isNaN(d)) return 'Choisir une date';
    return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  })();

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
        <window.TripTypeTabs
          value={tripType}
          onChange={(t) => onChange({ ...values, tripType: t })}
        />
      </div>
    <div className="va-search">
      {/* Départ */}
      <div className="va-search__field" onClick={(e) => { e.stopPropagation(); setEditing('depart'); }}>
        <span className="va-search__label">Départ</span>
        {editing === 'depart' ? (
          <Autocomplete
            value={values.depart}
            type={type}
            placeholder="Ville, gare, aéroport…"
            onChange={(v) => set('depart', v)}
            onPick={(it) => { set('depart', it.nom); setEditing(null); }}
          />
        ) : (
          <>
            <span className="va-search__value">
              <IMapPin size={16} style={{ color: 'var(--va-text-muted)' }} />
              {values.depart || 'D’où partez-vous ?'}
            </span>
            <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>Cliquer pour modifier</span>
          </>
        )}
      </div>

      <button
        className="va-search__swap"
        title="Inverser"
        type="button"
        onClick={(e) => { e.stopPropagation(); onChange({ ...values, depart: values.arrivee, arrivee: values.depart }); }}
      >
        <ISwap size={15} />
      </button>

      {/* Arrivée */}
      <div className="va-search__field" onClick={(e) => { e.stopPropagation(); setEditing('arrivee'); }}>
        <span className="va-search__label">Arrivée</span>
        {editing === 'arrivee' ? (
          <Autocomplete
            value={values.arrivee}
            type={type}
            placeholder="Ville, gare, aéroport…"
            onChange={(v) => set('arrivee', v)}
            onPick={(it) => { set('arrivee', it.nom); setEditing(null); }}
          />
        ) : (
          <>
            <span className="va-search__value">
              <IMapPin size={16} style={{ color: 'var(--va-text-muted)' }} />
              {values.arrivee || 'Où allez-vous ?'}
            </span>
            <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>Cliquer pour modifier</span>
          </>
        )}
      </div>

      {/* Date aller */}
      <div className="va-search__field" onClick={(e) => { e.stopPropagation(); setEditing('date'); }}>
        <span className="va-search__label">{tripType === 'retour' ? 'Date retour' : roundTrip ? 'Date aller' : 'Date'}</span>
        {editing === 'date' ? (
          <input
            type="date"
            autoFocus
            value={values.date || ''}
            onChange={(e) => set('date', e.target.value)}
            onBlur={() => setEditing(null)}
            style={{
              width: '100%', height: 38, padding: '0 12px',
              border: '1px solid var(--va-border)', borderRadius: 8,
              fontSize: 14, fontFamily: 'inherit', color: 'var(--va-text)',
              background: 'var(--va-bg)',
            }}
          />
        ) : (
          <>
            <span className="va-search__value">
              <ICalendar size={16} style={{ color: 'var(--va-text-muted)' }} />
              {dateLabel}
            </span>
            <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>Cliquer pour modifier</span>
          </>
        )}
      </div>

      {roundTrip && (
        <div className="va-search__field" onClick={(e) => { e.stopPropagation(); setEditing('dateRetour'); }}>
          <span className="va-search__label">Date retour</span>
          {editing === 'dateRetour' ? (
            <input
              type="date"
              autoFocus
              value={values.dateRetour || ''}
              min={values.date || undefined}
              onChange={(e) => set('dateRetour', e.target.value)}
              onBlur={() => setEditing(null)}
              style={{
                width: '100%', height: 38, padding: '0 12px',
                border: '1px solid var(--va-border)', borderRadius: 8,
                fontSize: 14, fontFamily: 'inherit', color: 'var(--va-text)',
                background: 'var(--va-bg)',
              }}
            />
          ) : (
            <>
              <span className="va-search__value">
                <ICalendar size={16} style={{ color: 'var(--va-text-muted)' }} />
                {retourLabel}
              </span>
              <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>Cliquer pour modifier</span>
            </>
          )}
        </div>
      )}

      {/* Voyageurs — popover adulte/enfant/bébé */}
      <div
        className="va-search__field"
        style={{ position: 'relative' }}
        onClick={(e) => { e.stopPropagation(); setEditing(editing === 'passagers' ? null : 'passagers'); }}
      >
        <span className="va-search__label">Voyageurs</span>
        <span className="va-search__value">
          <IUsers size={16} style={{ color: 'var(--va-text-muted)' }} />
          {window.paxLabel(window.normalizePax(values))}
        </span>
        <span style={{ fontSize: 12, color: 'var(--va-text-muted)' }}>
          {window.paxBreakdown(window.normalizePax(values)) || 'Cliquer pour modifier'}
        </span>
        {editing === 'passagers' && (
          <div
            style={{ position: 'absolute', top: 'calc(100% + 8px)', right: 0, zIndex: 30 }}
            onClick={(e) => e.stopPropagation()}
          >
            <window.PaxStepper
              value={window.normalizePax(values)}
              onChange={(pax) => onChange({ ...values, pax, passagers: window.paxCount(pax) })}
              onValidate={() => setEditing(null)}
            />
          </div>
        )}
      </div>

      <button
        type="button"
        className="va-search__cta"
        onClick={(e) => { e.stopPropagation(); setEditing(null); onSearch(values); }}
      >
        <ISearch size={16} />
        Rechercher
      </button>
    </div>
    </div>
  );
};

Object.assign(window, { Autocomplete, SearchBarEditable });
