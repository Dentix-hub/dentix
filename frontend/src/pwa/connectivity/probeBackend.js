import axios from 'axios';
import { API_URL } from '@/api/apiClient';

const PROBE_TIMEOUT_MS = 5000;

/**
 * Lightweight same-origin backend reachability probe (plan §10.1).
 * Hits the public health endpoint; carries no PHI and no credentials beyond
 * normal cookies. Returns true only when the backend actually answered.
 */
export async function probeBackend({ timeoutMs = PROBE_TIMEOUT_MS } = {}) {
    try {
        const response = await axios.get(`${API_URL}/api/v1/health`, {
            timeout: timeoutMs,
            withCredentials: true,
            headers: { 'X-Dentix-Connectivity-Probe': '1' },
        });
        return response.status === 200;
    } catch {
        return false;
    }
}
