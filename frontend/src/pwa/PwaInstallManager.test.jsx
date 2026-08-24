import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const pwaMocks = vi.hoisted(() => ({
    setNeedRefresh: vi.fn(),
    updateServiceWorker: vi.fn(),
}));

vi.mock('virtual:pwa-register/react', () => ({
    useRegisterSW: () => ({
        needRefresh: [false, pwaMocks.setNeedRefresh],
        offlineReady: [false, vi.fn()],
        updateServiceWorker: pwaMocks.updateServiceWorker,
    }),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => `translated:${key}`,
    }),
}));

import { PwaInstallManager } from './PwaInstallManager';
import { useInstallStore } from './installState';

const ENGAGEMENT_MS = 20 * 1000;
const originalUserAgent = window.navigator.userAgent;

function setUserAgent(ua) {
    Object.defineProperty(window.navigator, 'userAgent', {
        value: ua,
        configurable: true,
    });
}

function fireBeforeInstallPrompt() {
    const event = new Event('beforeinstallprompt');
    event.preventDefault = vi.fn();
    event.prompt = vi.fn();
    event.userChoice = Promise.resolve({ outcome: 'accepted' });
    act(() => {
        window.dispatchEvent(event);
    });
    return event;
}

describe('PwaInstallManager platform-aware install UX', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        window.localStorage.clear();
        useInstallStore.getState().resetForTests();
        setUserAgent(originalUserAgent);
    });

    afterEach(() => {
        vi.useRealTimers();
        setUserAgent(originalUserAgent);
    });

    it('never renders install UI at first paint even when the prompt is available', () => {
        setUserAgent('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36');
        render(<PwaInstallManager />);
        fireBeforeInstallPrompt();
        expect(screen.queryByText('translated:pwa.install.title')).not.toBeInTheDocument();
    });

    it('shows the Android install card after engagement and honors dismissal', () => {
        setUserAgent('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36');
        render(<PwaInstallManager />);
        fireBeforeInstallPrompt();

        act(() => {
            vi.advanceTimersByTime(ENGAGEMENT_MS);
        });
        expect(screen.getByText('translated:pwa.install.title')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'translated:pwa.install.later' }));
        expect(screen.queryByText('translated:pwa.install.title')).not.toBeInTheDocument();
    });

    it('triggers the native prompt only from an explicit user action', async () => {
        setUserAgent('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36');
        render(<PwaInstallManager />);
        const event = fireBeforeInstallPrompt();

        act(() => {
            vi.advanceTimersByTime(ENGAGEMENT_MS);
        });
        expect(event.prompt).not.toHaveBeenCalled();

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'translated:pwa.install.action' }));
        });
        expect(event.prompt).toHaveBeenCalledTimes(1);
    });

    it('shows iOS Add to Home Screen instructions instead of a native prompt', () => {
        setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1');
        render(<PwaInstallManager />);

        act(() => {
            vi.advanceTimersByTime(ENGAGEMENT_MS);
        });
        expect(screen.getByText('translated:pwa.install.ios.title')).toBeInTheDocument();
        expect(screen.getByText('translated:pwa.install.ios.step2')).toBeInTheDocument();
        expect(screen.queryByText('translated:pwa.install.title')).not.toBeInTheDocument();
    });

    it('renders nothing when running standalone or after appinstalled', () => {
        const previousMatchMedia = window.matchMedia;
        window.matchMedia = vi.fn().mockImplementation((query) => ({
            matches: query === '(display-mode: standalone)',
            media: query,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
        }));
        setUserAgent('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36');
        render(<PwaInstallManager />);
        fireBeforeInstallPrompt();

        act(() => {
            vi.advanceTimersByTime(ENGAGEMENT_MS);
        });
        expect(screen.queryByText('translated:pwa.install.title')).not.toBeInTheDocument();

        act(() => {
            window.dispatchEvent(new Event('appinstalled'));
        });
        expect(useInstallStore.getState().installed).toBe(true);
        window.matchMedia = previousMatchMedia;
    });
});
