function stripLeadingWww(hostname) {
    return hostname.toLowerCase().replace(/^www\./, '');
}

function isSameSiteWwwAlias(configuredUrl, locationLike) {
    return configuredUrl.protocol === locationLike.protocol
        && configuredUrl.port === locationLike.port
        && configuredUrl.pathname === '/'
        && stripLeadingWww(configuredUrl.hostname) === stripLeadingWww(locationLike.hostname);
}

export function resolveApiBaseUrl(configuredBaseUrl, locationLike) {
    if (configuredBaseUrl) {
        try {
            const configuredUrl = new URL(configuredBaseUrl, locationLike.origin);
            if (isSameSiteWwwAlias(configuredUrl, locationLike)) {
                return '';
            }
        } catch {
            // Preserve the configured value so Axios reports the configuration error.
        }
        return configuredBaseUrl;
    }

    const { hostname, protocol } = locationLike;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^(\d{1,3}\.){3}\d{1,3}$/.test(hostname)) {
        return `${protocol}//${hostname}:8000`;
    }

    return '';
}
