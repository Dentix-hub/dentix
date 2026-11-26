import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CONNECTION_STATES, useConnectivityStore } from '@/pwa/connectivity/connectivityStore';

const evaluateMocks = vi.hoisted(() => ({
    evaluateConnectivity: vi.fn(),
}));

vi.mock('@/pwa/connectivity/useConnectivity', () => ({
    useConnectivity: () => {},
    evaluateConnectivity: evaluateMocks.evaluateConnectivity,
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => `translated:${key}`,
    }),
}));

import NetworkStatusBanner from './NetworkStatusBanner';

function setState(state) {
    useConnectivityStore.setState({ state });
}

describe('NetworkStatusBanner', () => {
    beforeEach(() => {
        evaluateMocks.evaluateConnectivity.mockClear();
        useConnectivityStore.getState().resetForTests();
    });

    it('renders nothing while ONLINE', () => {
        setState(CONNECTION_STATES.ONLINE);
        const { container } = render(<NetworkStatusBanner />);
        expect(container).toBeEmptyDOMElement();
    });

    it('shows the offline banner with explicit high-contrast text and a manual retry action', () => {
        setState(CONNECTION_STATES.OFFLINE);
        render(<NetworkStatusBanner />);

        const banner = screen.getByTestId('network-status-banner');
        const message = screen.getByText('translated:connectivity.offline');
        const retryButton = screen.getByRole('button', { name: /translated:connectivity.retry/ });

        expect(banner).toBeInTheDocument();
        expect(banner).toHaveClass('bg-red-700', 'text-white');
        expect(message).toHaveClass('text-white', 'dark:text-white');
        expect(retryButton).toHaveClass('bg-red-800', 'text-white', 'hover:bg-red-900', 'focus-visible:ring-2');

        fireEvent.click(retryButton);
        expect(evaluateMocks.evaluateConnectivity).toHaveBeenCalledTimes(1);
    });

    it('distinguishes backend-degraded from offline with explicit dark foreground and high-contrast retry', () => {
        setState(CONNECTION_STATES.DEGRADED);
        render(<NetworkStatusBanner />);

        const banner = screen.getByTestId('network-status-banner');
        const message = screen.getByText('translated:connectivity.degraded');
        const retryButton = screen.getByRole('button', { name: /translated:connectivity.retry/ });

        expect(banner).toHaveClass('bg-amber-500', 'text-slate-950');
        expect(message).toHaveClass('text-slate-950', 'dark:text-slate-950');
        expect(retryButton).toHaveClass('bg-slate-900', 'text-white', 'hover:bg-slate-800', 'focus-visible:ring-2');

        fireEvent.click(retryButton);
        expect(evaluateMocks.evaluateConnectivity).toHaveBeenCalledTimes(1);
    });

    it('shows the recovering state with accessible white-on-sky contrast and without a retry button', () => {
        setState(CONNECTION_STATES.RECOVERING);
        render(<NetworkStatusBanner />);

        const banner = screen.getByTestId('network-status-banner');
        const message = screen.getByText('translated:connectivity.recovering');

        expect(banner).toHaveClass('bg-sky-700', 'text-white');
        expect(message).toHaveClass('text-white', 'dark:text-white');
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
