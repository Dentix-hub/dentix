const AUTH_ONLY_PATHS = new Set([
    '/',
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
]);

const PUBLIC_OR_RESERVED_PREFIXES = ['/ar', '/en', '/api', '/marketing'];

/**
 * Resolve a safe in-app redirect path after authentication.
 * Falls back to '/' for clinic users and '/admin' for super_admin.
 */
export function resolvePostLoginPath(role, fromLocation) {
    if (role === 'super_admin') {
        return '/admin';
    }

    let pathname = '';
    let search = '';
    let hash = '';

    if (typeof fromLocation === 'string') {
        try {
            const parsed = new URL(fromLocation, 'https://app.invalid');
            if (parsed.origin !== 'https://app.invalid' || !fromLocation.startsWith('/') || fromLocation.startsWith('//')) {
                return '/';
            }
            pathname = parsed.pathname;
            search = parsed.search;
            hash = parsed.hash;
        } catch {
            return '/';
        }
    } else if (fromLocation && typeof fromLocation === 'object' && typeof fromLocation.pathname === 'string') {
        pathname = fromLocation.pathname;
        search = typeof fromLocation.search === 'string' ? fromLocation.search : '';
        hash = typeof fromLocation.hash === 'string' ? fromLocation.hash : '';
    } else {
        return '/';
    }

    if (!pathname.startsWith('/') || pathname.startsWith('//')) {
        return '/';
    }

    if (AUTH_ONLY_PATHS.has(pathname)) {
        return '/';
    }

    const hitsReservedPrefix = PUBLIC_OR_RESERVED_PREFIXES.some(
        (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
    );
    if (hitsReservedPrefix) {
        return '/';
    }

    return `${pathname}${search}${hash}`;
}
