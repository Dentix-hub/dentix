/**
 * Safely extracts a human-readable string from an Axios / FastAPI error response.
 * Prevents structured validation details (e.g. FastAPI 422 array of objects or dict details)
 * from being passed directly into React children or toast notifications.
 */
function extractDetailText(detail) {
    if (!detail) return '';
    if (typeof detail === 'string') return detail.trim();
    if (Array.isArray(detail)) {
        const parts = [];
        for (const item of detail) {
            const text = extractDetailText(item);
            if (text && !parts.includes(text)) {
                parts.push(text);
            }
        }
        return parts.join('; ');
    }
    if (typeof detail === 'object') {
        const candidate = detail.msg ?? detail.message ?? detail.detail ?? detail.error;
        if (candidate) {
            return extractDetailText(candidate);
        }
        return '';
    }
    if (typeof detail === 'number' || typeof detail === 'boolean') {
        return String(detail);
    }
    return '';
}

export function formatApiError(error, fallback = 'Request failed') {
    const safeFallback = typeof fallback === 'string' && fallback.trim() ? fallback.trim() : 'Request failed';
    if (!error) return safeFallback;
    if (typeof error === 'string') return error.trim() || safeFallback;

    const responseData = error?.response?.data;
    const candidates = [
        responseData?.detail,
        responseData?.error?.details?.message,
        responseData?.error?.message,
        responseData?.message,
        error?.message,
    ];

    for (const candidate of candidates) {
        const text = extractDetailText(candidate);
        if (text) return text;
    }

    return safeFallback;
}
