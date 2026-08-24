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

    it('shows the offline banner with a manual retry action', () => {
        setState(CONNECTION_STATES.OFFLINE);
        render(<NetworkStatusBanner />);

        expect(screen.getByTestId('network-status-banner')).toBeInTheDocument();
        expect(screen.getByText('translated:connectivity.offline')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /translated:connectivity.retry/ }));
        expect(evaluateMocks.evaluateConnectivity).toHaveBeenCalledTimes(1);
    });

    it('distinguishes backend-degraded from offline', () => {
        setState(CONNECTION_STATES.DEGRADED);
        render(<NetworkStatusBanner />);
        expect(screen.getByText('translated:connectivity.degraded')).toBeInTheDocument();
    });

    it('shows the recovering state without a retry button', () => {
        setState(CONNECTION_STATES.RECOVERING);
        render(<NetworkStatusBanner />);
        expect(screen.getByText('translated:connectivity.recovering')).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
