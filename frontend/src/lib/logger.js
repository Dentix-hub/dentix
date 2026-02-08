import axios from 'axios';
import { API_URL } from '@/api';

const LOG_ENDPOINT = '/api/v1/system/logs';

export const logger = {
    error: async (message, stack = null, componentStack = null) => {
        try {
            // Prevent recursive logging if the logger itself fails
            const payload = {
                level: 'ERROR',
                source: 'FRONTEND',
                message: message?.toString() || 'Unknown Error',
                stack_trace: stack ? `Stack: ${stack} \nComponent: ${componentStack} ` : null,
                path: window.location.pathname,
                user_agent: navigator.userAgent
            };

            // Use fetch to avoid axios interceptor loops if axios is broken
            await fetch(`${API_URL}${LOG_ENDPOINT} `, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            console.error('[SystemLogger] Error reported:', message);

        } catch (err) {
            console.error('[SystemLogger] Failed to report error:', err);
        }
    },

    info: (message) => {
        console.log('[SystemLogger]', message);
        // Optional: Send info logs to backend if needed
    }
};
