/* Voyage Assistant — moteur de traduction (FR / EN / ES).

   Principe : les chaînes restent écrites EN FRANÇAIS dans le code (= clé).
   `t('Se connecter')` renvoie la traduction selon la langue courante, ou la
   chaîne française telle quelle si la langue est 'fr' ou si la clé manque.

   Réactivité : un seul composant (VoyageApp, la racine) s'abonne via useT().
   Au changement de langue, toute l'arborescence se re-rend, donc tous les
   appels t() recalculent la bonne langue — pas besoin d'abonner chaque
   composant individuellement.

   Le dictionnaire est défini dans i18n-dict.js (window.VA_DICT), chargé avant. */

(function () {
  const LANGS = ['fr', 'en', 'es'];
  const LABELS = { fr: 'Français', en: 'English', es: 'Español' };
  const LOCALES = { fr: 'fr-FR', en: 'en-GB', es: 'es-ES' };
  const DICT = (window.VA_DICT && typeof window.VA_DICT === 'object')
    ? window.VA_DICT
    : { en: {}, es: {} };

  let lang = (function () {
    try { return localStorage.getItem('va.lang') || 'fr'; } catch { return 'fr'; }
  })();
  if (LANGS.indexOf(lang) === -1) lang = 'fr';

  const subscribers = new Set();

  function getLang() { return lang; }
  function locale() { return LOCALES[lang] || 'fr-FR'; }

  function setLang(next) {
    if (LANGS.indexOf(next) === -1 || next === lang) return;
    lang = next;
    try { localStorage.setItem('va.lang', next); } catch {}
    try { document.documentElement.lang = next; } catch {}
    subscribers.forEach((fn) => { try { fn(next); } catch {} });
  }

  function translate(s) {
    if (s == null) return s;
    if (lang === 'fr') return s;
    const table = DICT[lang];
    if (table && Object.prototype.hasOwnProperty.call(table, s)) return table[s];
    return s; // repli : on affiche le français plutôt que de casser
  }

  // t('Bonjour {name}', { name: 'Léa' }) -> interpolation simple {clé}
  function t(s, vars) {
    let out = translate(s);
    if (vars && typeof out === 'string') {
      Object.keys(vars).forEach((k) => {
        out = out.split('{' + k + '}').join(String(vars[k]));
      });
    }
    return out;
  }

  // Hook de réactivité — appelé UNIQUEMENT par la racine VoyageApp.
  function useT() {
    const [, force] = React.useState(0);
    React.useEffect(() => {
      const fn = () => force((x) => x + 1);
      subscribers.add(fn);
      return () => { subscribers.delete(fn); };
    }, []);
    return { t, lang, setLang, locale: locale() };
  }

  try { document.documentElement.lang = lang; } catch {}

  window.VA_I18N = { LANGS, LABELS, LOCALES, getLang, setLang, locale, t, translate, useT };
  window.t = t;
  window.useT = useT;
})();
