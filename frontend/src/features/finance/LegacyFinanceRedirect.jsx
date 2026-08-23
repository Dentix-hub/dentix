import { Navigate, useLocation } from 'react-router-dom';

/**
 * Compatibility redirect for legacy Finance bookmarks.
 * Preserve query/hash so date and identifier filters are not silently lost.
 */
export default function LegacyFinanceRedirect({ to }) {
    const location = useLocation();

    return (
        <Navigate
            replace
            to={{
                pathname: to,
                search: location.search,
                hash: location.hash,
            }}
        />
    );
}
