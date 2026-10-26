/**
 * Frontend Performance Diagnostics (PR4).
 * Dev/staging-only timing log of API calls during first load of Dashboard,
 * Patients list, and Patient details (count, parallelism, each duration).
 * 
 * Strict rule: No behavior change in production.
 */

import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export const isPerfDiagnosticsEnabled = () => {
    if (typeof window === 'undefined') return false;
    try {
        const isFlag = window.localStorage?.getItem('PERF_DIAGNOSTICS') === '1';
        const isStaging = typeof window.location?.hostname === 'string' && window.location.hostname.includes('staging');
        const isDev = Boolean(import.meta?.env?.DEV) && import.meta?.env?.MODE !== 'test';
        return isFlag || isStaging || isDev;
    } catch {
        return false;
    }
};

let activeInFlight = 0;
let requestCounter = 0;

let currentSession = null;
const recordedRoutes = new Set();

export function setupApiPerfInterceptor(axiosInstance) {
    if (!isPerfDiagnosticsEnabled() || !axiosInstance?.interceptors?.request || !axiosInstance?.interceptors?.response) {
        return;
    }

    axiosInstance.interceptors.request.use((config) => {
        if (!isPerfDiagnosticsEnabled()) return config;

        activeInFlight += 1;
        config._perf = {
            id: ++requestCounter,
            start: performance.now(),
            activeAtStart: activeInFlight,
        };

        if (currentSession) {
            currentSession.peakParallelism = Math.max(
                currentSession.peakParallelism,
                activeInFlight
            );
        }

        return config;
    });

    const handleSettled = (responseOrError, isError = false) => {
        if (!isPerfDiagnosticsEnabled()) return;

        activeInFlight = Math.max(0, activeInFlight - 1);

        const config = isError
            ? responseOrError?.config
            : responseOrError?.config;
        const perf = config?._perf;

        if (perf) {
            const duration = performance.now() - perf.start;
            const entry = {
                id: perf.id,
                url: config.url || '',
                method: (config.method || 'GET').toUpperCase(),
                durationMs: Number(duration.toFixed(2)),
                status: isError ? responseOrError?.response?.status || 'ERR' : responseOrError?.status || 200,
                serverTiming: !isError ? responseOrError?.headers?.['server-timing'] || '-' : '-',
                parallelAtStart: perf.activeAtStart,
            };

            if (currentSession) {
                currentSession.requests.push(entry);
                currentSession.resetTimer();
            }
        }
    };

    axiosInstance.interceptors.response.use(
        (response) => {
            handleSettled(response, false);
            return response;
        },
        (error) => {
            handleSettled(error, true);
            return Promise.reject(error);
        }
    );
}

export function startRoutePerfSession(routeKey) {
    if (!isPerfDiagnosticsEnabled()) return;
    if (recordedRoutes.has(routeKey)) return;

    if (currentSession) {
        finishSession(currentSession);
    }

    const session = {
        routeKey,
        startTime: performance.now(),
        requests: [],
        peakParallelism: activeInFlight,
        timer: null,
        resetTimer() {
            if (this.timer) clearTimeout(this.timer);
            // Settle 1500ms after last response or after max timeout
            this.timer = setTimeout(() => {
                finishSession(session);
            }, 1500);
        },
    };

    currentSession = session;
    session.resetTimer();

    // 4s hard cutoff
    setTimeout(() => {
        if (currentSession === session) {
            finishSession(session);
        }
    }, 4000);
}

export function finishSession(session) {
    if (!session || recordedRoutes.has(session.routeKey)) return;
    if (session.timer) clearTimeout(session.timer);
    recordedRoutes.add(session.routeKey);

    if (currentSession === session) {
        currentSession = null;
    }

    const totalRequests = session.requests.length;
    const totalDuration = (performance.now() - session.startTime).toFixed(2);

    console.group(`%c[PERF_TIMING] First Load: ${session.routeKey}`, 'color: #00bcd4; font-weight: bold;');
    console.log(
        `Total API Calls: ${totalRequests} | Peak Parallelism: ${session.peakParallelism} | Window: ${totalDuration}ms`
    );
    if (totalRequests > 0) {
        console.table(
            session.requests.map((r) => ({
                Method: r.method,
                Endpoint: r.url,
                'Duration (ms)': r.durationMs,
                Status: r.status,
                'Server-Timing': r.serverTiming,
            }))
        );
    } else {
        console.log('No API calls captured during this route load window.');
    }
    console.groupEnd();
}

export function resetRecordedRoutesForTesting() {
    recordedRoutes.clear();
    currentSession = null;
    activeInFlight = 0;
    requestCounter = 0;
}

export function RoutePerfDiagnostics() {
    const location = useLocation();

    useEffect(() => {
        if (!isPerfDiagnosticsEnabled()) return;
        const path = location.pathname;

        let routeKey = null;
        if (path === '/' || path === '/dashboard') {
            routeKey = 'Dashboard (/)';
        } else if (path === '/patients') {
            routeKey = 'Patients List (/patients)';
        } else if (path.startsWith('/patients/') && path.split('/').filter(Boolean).length === 2) {
            routeKey = 'Patient Details (/patients/:id)';
        }

        if (routeKey) {
            startRoutePerfSession(routeKey);
        }
    }, [location.pathname]);

    return null;
}
