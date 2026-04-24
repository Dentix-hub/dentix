export function parseJwt(token) {
    try {
        if (!token) return null;
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}


// SECURITY: Tokens are stored only in sessionStorage (cleared on tab close)
// Backend also sets httpOnly cookies for automatic transmission.
// Avoid localStorage to prevent XSS token theft.

export function getToken() {
    return sessionStorage.getItem('token');
}

export function getRefreshToken() {
    return sessionStorage.getItem('refresh_token');
}

export function setToken(token, refreshToken = null) {
    sessionStorage.setItem('token', token);
    if (refreshToken) {
        sessionStorage.setItem('refresh_token', refreshToken);
    }
}

export function removeToken() {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('refresh_token');
}
