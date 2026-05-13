// Déclenche `onTimeout` si l'utilisateur n'interagit pas pendant `delayMs`.
// On considère "interaction" : envoi d'un message, mouvement de souris, clic, frappe.
// `reset()` est exposé pour réarmer le timer manuellement après une action significative.

import { useCallback, useEffect, useRef } from "react";

export function useInactivity(
  delayMs: number,
  onTimeout: () => void,
  enabled: boolean,
) {
  const timerRef = useRef<number | null>(null);
  const callbackRef = useRef(onTimeout);
  callbackRef.current = onTimeout;

  const clear = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clear();
    if (!enabled) return;
    timerRef.current = window.setTimeout(() => {
      callbackRef.current();
    }, delayMs);
  }, [clear, delayMs, enabled]);

  useEffect(() => {
    if (!enabled) {
      clear();
      return;
    }
    reset();
    const events = ["mousemove", "mousedown", "keydown", "touchstart"];
    events.forEach((e) => window.addEventListener(e, reset));
    return () => {
      clear();
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [enabled, clear, reset]);

  return { reset, clear };
}
