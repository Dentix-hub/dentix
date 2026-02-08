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


export function getToken() {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
}

export function getRefreshToken() {
    return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
}

export function setToken(token, refreshToken = null, remember = true) {
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('token', token);
    if (refreshToken) {
        storage.setItem('refresh_token', refreshToken);
    }
}

export function removeToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('refresh_token');
}
