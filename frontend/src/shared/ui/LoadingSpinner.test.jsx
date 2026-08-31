import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import LoadingSpinner from './LoadingSpinner';

describe('Dentix shared LoadingSpinner public contract', () => {
    describe('default and "page" variant', () => {
        it('renders default page variant with pulse tooth SVG, outer glow ring, and 3 pulse dots', () => {
            const { container } = render(<LoadingSpinner />);
            const root = container.firstElementChild;

            expect(root).toBeInTheDocument();
            expect(root).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'min-h-[200px]', 'gap-4');

            // Outer glow ring
            const glowRing = container.querySelector('.animate-ping');
            expect(glowRing).toBeInTheDocument();
            expect(glowRing).toHaveClass('rounded-full', 'bg-primary/10');
            expect(glowRing.style.animationDuration).toBe('2s');

            // Animated tooth SVG
            const svg = container.querySelector('svg');
            expect(svg).toBeInTheDocument();
            expect(svg).toHaveClass('w-7', 'h-7', 'text-primary', 'animate-pulse');
            expect(svg.style.animationDuration).toBe('1.5s');

            // 3 animated loading dots with incremental delay
            const dots = container.querySelectorAll('.bg-primary\\/60');
            expect(dots).toHaveLength(3);
            expect(dots[0].style.animationDelay).toBe('0s');
            expect(dots[1].style.animationDelay).toBe('0.15s');
            expect(dots[2].style.animationDelay).toBe('0.3s');
            dots.forEach((dot) => {
                expect(dot).toHaveClass('w-1.5', 'h-1.5', 'rounded-full');
            });
        });

        it('renders explicit variant="page" identically to default', () => {
            const { container } = render(<LoadingSpinner variant="page" />);
            const root = container.firstElementChild;

            expect(root).toBeInTheDocument();
            expect(root).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'min-h-[200px]', 'gap-4');
            expect(container.querySelector('svg')).toBeInTheDocument();
            expect(container.querySelectorAll('.bg-primary\\/60')).toHaveLength(3);
        });

        it('forwards custom className to root container for page variant', () => {
            const { container } = render(<LoadingSpinner className="custom-page-loader" />);
            expect(container.firstElementChild).toHaveClass('custom-page-loader');
        });
    });

    describe('"inline" variant', () => {
        it('renders inline variant with spinner borders and forwards custom className', () => {
            const { container } = render(<LoadingSpinner variant="inline" className="custom-inline-loader" />);
            const root = container.firstElementChild;

            expect(root).toBeInTheDocument();
            expect(root).toHaveClass('inline-flex', 'items-center', 'justify-center', 'custom-inline-loader');

            const spinRing = container.querySelector('.animate-spin');
            expect(spinRing).toBeInTheDocument();
            expect(spinRing).toHaveClass('rounded-full', 'border-2', 'border-transparent', 'border-t-primary');

            const bgRing = container.querySelector('.border-primary\\/20');
            expect(bgRing).toBeInTheDocument();
            expect(bgRing).toHaveClass('rounded-full', 'border-2');

            // Must not contain page SVG or shimmer rows
            expect(container.querySelector('svg')).not.toBeInTheDocument();
            expect(container.querySelector('.animate-shimmer')).not.toBeInTheDocument();
        });
    });

    describe('"shimmer" variant', () => {
        it('renders 3 placeholder rows with defined widths and animationDelay values without snapshots', () => {
            const { container } = render(<LoadingSpinner variant="shimmer" className="custom-shimmer-loader" />);
            const root = container.firstElementChild;

            expect(root).toBeInTheDocument();
            expect(root).toHaveClass('space-y-4', 'custom-shimmer-loader');

            const shimmerRows = container.querySelectorAll('.animate-shimmer');
            expect(shimmerRows).toHaveLength(3);

            // Row 1: width 3/4, no explicit animationDelay override
            expect(shimmerRows[0]).toHaveClass('h-4', 'bg-slate-200', 'dark:bg-slate-700', 'rounded-full', 'w-3/4');
            expect(shimmerRows[0].style.animationDelay).toBe('');

            // Row 2: width 1/2, animationDelay 0.15s
            expect(shimmerRows[1]).toHaveClass('h-4', 'bg-slate-200', 'dark:bg-slate-700', 'rounded-full', 'w-1/2');
            expect(shimmerRows[1].style.animationDelay).toBe('0.15s');

            // Row 3: width 5/6, animationDelay 0.3s
            expect(shimmerRows[2]).toHaveClass('h-4', 'bg-slate-200', 'dark:bg-slate-700', 'rounded-full', 'w-5/6');
            expect(shimmerRows[2].style.animationDelay).toBe('0.3s');

            // Must not contain page SVG or inline spinner
            expect(container.querySelector('svg')).not.toBeInTheDocument();
            expect(container.querySelector('.animate-spin')).not.toBeInTheDocument();
        });
    });
});
