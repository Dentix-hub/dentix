import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RevenueChart, StatusChart } from './DashboardCharts';

describe('Dashboard charts render real Recharts series', () => {
    beforeEach(() => {
        vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function () {
            const width = this.tagName === 'SPAN' ? this.textContent.length * 7 : 600;
            const height = this.tagName === 'SPAN' ? 14 : 260;
            return { width, height, top: 0, left: 0, bottom: height, right: width };
        });
        vi.stubGlobal('ResizeObserver', class {
            constructor(callback) { this.callback = callback; }
            observe() { this.callback([{ contentRect: { width: 600, height: 260 } }]); }
            unobserve() {}
            disconnect() {}
        });
    });
    afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

    it('draws the revenue area and axes from the supplied server values', async () => {
        const { container } = render(
            <RevenueChart
                data={[{ name: '2026-10-29', revenue: 100 }, { name: '2026-10-30', revenue: 300 }]}
                formatCurrency={value => `${value} EGP`}
                revenueLabel="الإيرادات"
            />,
        );
        await waitFor(() => expect(container.querySelector('.recharts-area-curve')).toBeTruthy());
        expect(screen.getByText('2026-10-29')).toBeInTheDocument();
        expect(screen.getByText('2026-10-30')).toBeInTheDocument();
        expect(container.querySelectorAll('.recharts-cartesian-axis').length).toBe(2);
    });

    it('draws a sector for each nonempty appointment status and labels the legend', async () => {
        const { container } = render(<StatusChart data={[
            { name: 'مكتمل', value: 2, fill: '#10b981' },
            { name: 'انتظار', value: 1, fill: '#f59e0b' },
        ]} />);
        await waitFor(() => expect(container.querySelectorAll('.recharts-pie-sector').length).toBe(2));
        expect(screen.getByText('مكتمل')).toBeInTheDocument();
        expect(screen.getByText('انتظار')).toBeInTheDocument();
    });
});
