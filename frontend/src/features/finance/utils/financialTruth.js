export function authoritativeNumber(value, fallback = 0) {
    if (value === null || value === undefined || value === '') {
        const fallbackNumber = Number(fallback);
        return Number.isFinite(fallbackNumber) ? fallbackNumber : 0;
    }

    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;

    const fallbackNumber = Number(fallback);
    return Number.isFinite(fallbackNumber) ? fallbackNumber : 0;
}
