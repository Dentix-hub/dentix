/**
 * Canonical build identity for diagnostics and stale-build support triage.
 * Values are injected by Vite `define` at build time (see vite.config.js);
 * a dev fallback keeps tests and the dev server working without a build step.
 */
/* global __BUILD_INFO__:readonly */

const DEV_FALLBACK = {
    sha: 'dev',
    shaShort: 'dev',
    builtAt: null,
    environment: 'development',
};

function readInjectedBuildInfo() {
    try {
        if (typeof __BUILD_INFO__ !== 'undefined' && __BUILD_INFO__) {
            return __BUILD_INFO__;
        }
    } catch {
        // Global not defined in this runtime; fall through to dev fallback.
    }
    return DEV_FALLBACK;
}

export const BUILD_INFO = Object.freeze(readInjectedBuildInfo());

export function getBuildLabel() {
    const sha = BUILD_INFO.shaShort || BUILD_INFO.sha || 'unknown';
    return `${sha}${BUILD_INFO.environment ? ` (${BUILD_INFO.environment})` : ''}`;
}
