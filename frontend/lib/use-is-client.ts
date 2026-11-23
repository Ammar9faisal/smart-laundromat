import { useSyncExternalStore } from "react";

const noSubscription = () => () => {};

/**
 * False during server rendering and hydration, true afterwards. Lets a
 * component read browser-only values (current time, the URL) in its initial
 * state without a hydration mismatch or a setState inside an effect.
 */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false
  );
}
