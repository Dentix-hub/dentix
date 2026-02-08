import http from 'k6/http';
import { check, fail } from 'k6';
import { config } from './config.js';

export function login(username, password) {
    const url = `${config.BASE_URL}/api/v1/token`;
    const payload = {
        username: username,
        password: password,
    };

    const params = {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    };

    const res = http.post(url, payload, params);

    const isSuccess = check(res, {
        'login successful': (r) => r.status === 200,
        'has access token': (r) => r.json('access_token') !== undefined,
    });

    if (!isSuccess) {
        console.error(`Login failed for user ${username}: ${res.status} ${res.body}`);
        return null;
    }

    return res.json('access_token');
}

export function getAuthHeaders(token) {
    return {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
    };
}

export function getRandomItem(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}
