/**
 * Returns true if app is running as installed PWA (standalone mode)
 * Works on Android Chrome, iOS Safari, and desktop
 */
export function isRunningAsPWA() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true ||
    document.referrer.includes('android-app://')
  );
}

/**
 * Returns true if we should show sidebar open by default
 * Never open by default on PWA or small screens
 */
export function shouldSidebarBeOpenByDefault() {
  if (window.innerWidth < 1024) return false; // Mobile/tablet = always closed
  return true;                                // Desktop browser/PWA = open by default
}
