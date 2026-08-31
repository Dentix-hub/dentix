import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Badge from './Badge';

describe('Dentix shared Badge public contract', () => {
    it('renders children with default variant and size classes', () => {
        render(<Badge>Active</Badge>);
        const badge = screen.getByText('Active');

        expect(badge).toBeInTheDocument();
        expect(badge.tagName).toBe('SPAN');
        expect(badge).toHaveClass(
            'inline-flex',
            'items-center',
            'justify-center',
            'font-bold',
            'rounded-full',
            'bg-slate-100',
            'text-slate-800',
            'dark:bg-slate-800',
            'dark:text-slate-200',
            'px-2.5',
            'py-0.5',
            'text-xs',
        );
    });

    it('renders non-default variants with expected styles', () => {
        const variantCases = [
            {
                variant: 'primary',
                expectedClasses: ['bg-primary/10', 'text-primary', 'border', 'border-primary/20'],
            },
            {
                variant: 'success',
                expectedClasses: ['bg-emerald-500/10', 'text-emerald-600', 'dark:text-emerald-400', 'border', 'border-emerald-500/20'],
            },
            {
                variant: 'warning',
                expectedClasses: ['bg-amber-500/10', 'text-amber-600', 'dark:text-amber-400', 'border', 'border-amber-500/20'],
            },
            {
                variant: 'danger',
                expectedClasses: ['bg-red-500/10', 'text-red-600', 'dark:text-red-400', 'border', 'border-red-500/20'],
            },
            {
                variant: 'info',
                expectedClasses: ['bg-blue-500/10', 'text-blue-600', 'dark:text-blue-400', 'border', 'border-blue-500/20'],
            },
        ];

        for (const { variant, expectedClasses } of variantCases) {
            const { unmount } = render(<Badge variant={variant}>{variant}</Badge>);
            const badge = screen.getByText(variant);
            expect(badge).toHaveClass(...expectedClasses);
            unmount();
        }
    });

    it('applies sm size classes', () => {
        render(<Badge size="sm">Small Badge</Badge>);
        const badge = screen.getByText('Small Badge');
        expect(badge).toHaveClass('px-2', 'py-0.5', 'text-[10px]');
    });

    it('applies lg size classes', () => {
        render(<Badge size="lg">Large Badge</Badge>);
        const badge = screen.getByText('Large Badge');
        expect(badge).toHaveClass('px-3', 'py-1', 'text-sm');
    });

    it('appends custom className extension without overriding base styles', () => {
        render(<Badge className="custom-badge-extra shadow-md">Custom Class</Badge>);
        const badge = screen.getByText('Custom Class');
        expect(badge).toHaveClass('custom-badge-extra', 'shadow-md');
        expect(badge).toHaveClass('inline-flex', 'items-center', 'justify-center', 'font-bold', 'rounded-full');
    });
});
