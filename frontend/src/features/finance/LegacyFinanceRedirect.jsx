import { Navigate, useLocation, useParams } from 'react-router-dom';

/**
 * Compatibility redirect for legacy Finance bookmarks.
 * Preserve query/hash so date and identifier filters are not silently lost.
 * `to` may be a pathname string or a function of route params for old detail
 * URLs that need to preserve an identifier in the canonical path.
 */
export default function LegacyFinanceRedirect({ to }) {
    const location = useLocation();
    const params = useParams();
    const pathname = typeof to === 'function' ? to(params) : to;

    return (
        <Navigate
            replace
            to={{
                pathname,
                search: location.search,
                hash: location.hash,
            }}
        />
    );
}
