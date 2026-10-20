import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ChartQuickActionLauncher from '../components/ChartQuickActionLauncher';
import {
    CANONICAL_PROCEDURES,
    CANONICAL_FINDINGS,
    getSmartTargetKindAndSurfaces,
    isAnteriorTooth,
    isPosteriorTooth,
} from '../domain/catalogDefinitions';
import { useAuthStore } from '@/store/auth.store';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            if (options && options.count !== undefined && typeof fallback === 'string') {
                return fallback.replace('{{count}}', options.count);
            }
            return typeof fallback === 'string' ? fallback : key;
        },
        i18n: { language: 'en' },
    }),
}));

describe('G8-M11: Smart Defaults driven by allowed_target_kinds', () => {
    it('correctly identifies anterior and posterior teeth by FDI tooth key', () => {
        expect(isAnteriorTooth('11')).toBe(true);
        expect(isAnteriorTooth('21')).toBe(true);
        expect(isAnteriorTooth('12')).toBe(true);
        expect(isAnteriorTooth('13')).toBe(true);
        expect(isAnteriorTooth('16')).toBe(false);

        expect(isPosteriorTooth('16')).toBe(true);
        expect(isPosteriorTooth('24')).toBe(true);
        expect(isPosteriorTooth('37')).toBe(true);
        expect(isPosteriorTooth('48')).toBe(true);
        expect(isPosteriorTooth('11')).toBe(false);
    });

    it('assigns O on Tooth 16 and I on Tooth 11 for surface-capable definitions (REST_COMPOSITE, CARIES, FRACTURE)', () => {
        const composite = CANONICAL_PROCEDURES.find((p) => p.code === 'REST_COMPOSITE');
        const caries = CANONICAL_FINDINGS.find((f) => f.code === 'CARIES');
        const fracture = CANONICAL_FINDINGS.find((f) => f.code === 'FRACTURE');

        // Tooth 16 (Posterior) -> default surface 'O'
        const res16Comp = getSmartTargetKindAndSurfaces(composite, '16', []);
        expect(res16Comp.targetKind).toBe('surface');
        expect(res16Comp.defaultSurface).toBe('O');
        expect(res16Comp.surfaces).toEqual(['O']);
        expect(res16Comp.requiresSurfacePrompt).toBe(true);

        const res16Caries = getSmartTargetKindAndSurfaces(caries, '16', []);
        expect(res16Caries.targetKind).toBe('surface');
        expect(res16Caries.defaultSurface).toBe('O');
        expect(res16Caries.surfaces).toEqual(['O']);

        const res16Fracture = getSmartTargetKindAndSurfaces(fracture, '16', []);
        expect(res16Fracture.targetKind).toBe('surface');
        expect(res16Fracture.defaultSurface).toBe('O');
        expect(res16Fracture.surfaces).toEqual(['O']);

        // Tooth 11 (Anterior) -> default surface 'I'
        const res11Comp = getSmartTargetKindAndSurfaces(composite, '11', []);
        expect(res11Comp.targetKind).toBe('surface');
        expect(res11Comp.defaultSurface).toBe('I');
        expect(res11Comp.surfaces).toEqual(['I']);
        expect(res11Comp.requiresSurfacePrompt).toBe(true);

        const res11Caries = getSmartTargetKindAndSurfaces(caries, '11', []);
        expect(res11Caries.targetKind).toBe('surface');
        expect(res11Caries.defaultSurface).toBe('I');
        expect(res11Caries.surfaces).toEqual(['I']);

        const res11Fracture = getSmartTargetKindAndSurfaces(fracture, '11', []);
        expect(res11Fracture.targetKind).toBe('surface');
        expect(res11Fracture.defaultSurface).toBe('I');
        expect(res11Fracture.surfaces).toEqual(['I']);
    });

    it('reuses existing surfaces when already selected on the tooth without prompting', () => {
        const composite = CANONICAL_PROCEDURES.find((p) => p.code === 'REST_COMPOSITE');
        const res = getSmartTargetKindAndSurfaces(composite, '16', ['M', 'O']);
        expect(res.targetKind).toBe('surface');
        expect(res.surfaces).toEqual(['M', 'O']);
        expect(res.requiresSurfacePrompt).toBe(false);
    });

    it('assigns tooth target kind for non-surface definitions (SURG_EXTRACTION, PROS_CROWN, ENDO_RCT)', () => {
        const extraction = CANONICAL_PROCEDURES.find((p) => p.code === 'SURG_EXTRACTION');
        const crown = CANONICAL_PROCEDURES.find((p) => p.code === 'PROS_CROWN');
        const rct = CANONICAL_PROCEDURES.find((p) => p.code === 'ENDO_RCT');

        const resExt = getSmartTargetKindAndSurfaces(extraction, '16', []);
        expect(resExt.targetKind).toBe('tooth');
        expect(resExt.surfaces).toEqual([]);
        expect(resExt.requiresSurfacePrompt).toBe(false);

        const resCrown = getSmartTargetKindAndSurfaces(crown, '16', []);
        expect(resCrown.targetKind).toBe('tooth');
        expect(resCrown.surfaces).toEqual([]);
        expect(resCrown.requiresSurfacePrompt).toBe(false);

        const resRct = getSmartTargetKindAndSurfaces(rct, '16', []);
        expect(resRct.targetKind).toBe('tooth');
        expect(resRct.surfaces).toEqual([]);
        expect(resRct.requiresSurfacePrompt).toBe(false);
    });
});

describe('U1 & G8: ChartQuickActionLauncher Real Clinic Catalog & Pricing', () => {
    const mockClinicProcedures = [
        { id: 1, name: 'حشو كومبوزيت -- Composite Filling Class I', canonical_code: 'REST_COMPOSITE', price: 600 },
        { id: 2, name: 'حشو عصب – Root Canal Treatment', canonical_code: 'ENDO_RCT', price: 1500 },
        { id: 3, name: 'تاج بورسلين – Porcelain Crown', canonical_code: 'PROS_CROWN', price: 2000 },
        { id: 4, name: 'خلع عادي – Simple Extraction', canonical_code: 'SURG_EXTRACTION', price: 300 },
        { id: 5, name: 'طقم مرن – Flexible Denture', canonical_code: 'PROS_DENTURE', price: 0 },
        { id: 6, name: 'Custom Whitening Procedure', canonical_code: null, price: 800 },
    ];

    beforeEach(() => {
        localStorage.clear();
        useAuthStore.setState({ user: { id: 42, tenant_id: 101, role: 'doctor' } });
    });

    it('1. renders real clinic procedures with real prices; seeded price=0 has no price label; no EGP or invented prices anywhere in DOM', () => {
        const { container } = render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-search')).toBeInTheDocument();

        // Default favorites: findings only (procedures start unstarred)
        expect(screen.getByTestId('chart-quick-action-favorites')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-CARIES')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-FRACTURE')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-PAIN')).toBeInTheDocument();

        // All procedures section renders real clinic procedures without searching
        expect(screen.getByTestId('chart-quick-action-all-procedures')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-REST_COMPOSITE')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-ENDO_RCT')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-PROS_CROWN')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-SURG_EXTRACTION')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-PROS_DENTURE')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-proc:6')).toBeInTheDocument();

        // Real prices are rendered
        expect(screen.getByText(/600/)).toBeInTheDocument();
        expect(screen.getByText(/1,500/)).toBeInTheDocument();
        expect(screen.getByText(/2,000/)).toBeInTheDocument();
        expect(screen.getByText(/300/)).toBeInTheDocument();

        // Seeded procedure with price 0 has NO price label
        const dentureCard = screen.getByTestId('chart-quick-action-item-PROS_DENTURE');
        expect(dentureCard.textContent).not.toMatch(/·\s*0/);

        // Invariant: no hardcoded "EGP" or old fake prices (150, 500, 1200, 2400, 3000, 2500)
        expect(container.textContent).not.toContain('EGP');
        expect(container.textContent).not.toContain('150 EGP');
        expect(container.textContent).not.toContain('500 EGP');
        expect(container.textContent).not.toContain('1200 EGP');
    });

    it('2. renders recents section when items are saved in localStorage under tenant/user-scoped key', () => {
        const recentsKey = 'dentix_chart_recents_101_42';
        localStorage.setItem(recentsKey, JSON.stringify(['proc:2', 'CARIES']));

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        expect(screen.getByTestId('chart-quick-action-recents')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-recent-item-ENDO_RCT')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-recent-item-CARIES')).toBeInTheDocument();
    });

    it('3. filters items in real time when searching in English and Arabic', () => {
        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        const searchInput = screen.getByTestId('chart-quick-action-search');

        // Search English
        fireEvent.change(searchInput, { target: { value: 'composite' } });
        expect(screen.getByTestId('chart-quick-action-item-REST_COMPOSITE')).toBeInTheDocument();
        expect(screen.queryByTestId('chart-quick-action-item-ENDO_RCT')).not.toBeInTheDocument();

        // Search Arabic (exact clinic procedure name has 'حشو عصب')
        fireEvent.change(searchInput, { target: { value: 'عصب' } });
        expect(screen.getByTestId('chart-quick-action-item-ENDO_RCT')).toBeInTheDocument();
        expect(screen.queryByTestId('chart-quick-action-item-REST_COMPOSITE')).not.toBeInTheDocument();

        // Search non-existing
        fireEvent.change(searchInput, { target: { value: 'xyzunknown' } });
        expect(screen.getByTestId('no-actions-found')).toBeInTheDocument();
    });

    it('4. stars and unstars actions, updating favorites in localStorage by item.key', () => {
        const favoritesKey = 'dentix_chart_favorites_101_42';

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        // Star composite procedure (key is 'proc:1')
        const favToggle = screen.getByTestId('favorite-toggle-REST_COMPOSITE');
        fireEvent.click(favToggle);

        const stored = JSON.parse(localStorage.getItem(favoritesKey) || '[]');
        expect(stored.includes('proc:1')).toBe(true);

        // Unstar again
        fireEvent.click(favToggle);
        const storedAfter = JSON.parse(localStorage.getItem(favoritesKey) || '[]');
        expect(storedAfter.includes('proc:1')).toBe(false);
    });

    it('5. executes a whole-tooth action immediately, updating recents in localStorage', () => {
        const onAction = vi.fn();
        const recentsKey = 'dentix_chart_recents_101_42';

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={onAction}
                clinicProcedures={mockClinicProcedures}
            />
        );

        const extractionItem = screen.getByTestId('chart-quick-action-item-SURG_EXTRACTION');
        fireEvent.click(extractionItem);

        expect(onAction).toHaveBeenCalledWith(
            expect.objectContaining({
                item: expect.objectContaining({
                    code: 'SURG_EXTRACTION',
                    procedureId: 4,
                    key: 'proc:4',
                    name: 'خلع عادي – Simple Extraction',
                }),
                toothKeys: ['16'],
                targetKind: 'tooth',
                surfaces: [],
            })
        );

        // Recents updated in localStorage by key
        const storedRecents = JSON.parse(localStorage.getItem(recentsKey) || '[]');
        expect(storedRecents[0]).toBe('proc:4');
    });

    it('6. opens surface prompt for surface-capable action when no surface was pre-selected, pre-selecting smart default', () => {
        const onAction = vi.fn();

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={onAction}
                clinicProcedures={mockClinicProcedures}
            />
        );

        // Tooth 16 (posterior) -> clicks Composite Restoration
        const compositeItem = screen.getByTestId('chart-quick-action-item-REST_COMPOSITE');
        fireEvent.click(compositeItem);

        // Surface prompt popover opens
        expect(screen.getByTestId('surface-prompt-popover')).toBeInTheDocument();
        // Smart default O is pre-selected for posterior tooth 16
        expect(screen.getByTestId('prompt-surface-pill-O')).toHaveAttribute('aria-pressed', 'true');

        // Toggle surface M
        fireEvent.click(screen.getByTestId('prompt-surface-pill-M'));

        // Click confirm
        fireEvent.click(screen.getByTestId('confirm-action-button'));

        expect(onAction).toHaveBeenCalledWith(
            expect.objectContaining({
                item: expect.objectContaining({ code: 'REST_COMPOSITE', procedureId: 1 }),
                toothKeys: ['16'],
                targetKind: 'surface',
                surfaces: expect.arrayContaining(['O', 'M']),
            })
        );
    });

    it('7. displays billing-only tag for items with canonical_code=null and hides it for mapped items', () => {
        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        // Custom procedure (id 6) has canonical_code=null -> billing-only tag shown
        expect(screen.getByTestId('billing-only-tag-proc:6')).toBeInTheDocument();
        expect(screen.getByTestId('billing-only-tag-proc:6')).toHaveTextContent(/Billing only/i);

        // Mapped procedure (id 1) has canonical_code='REST_COMPOSITE' -> no tag
        expect(screen.queryByTestId('billing-only-tag-REST_COMPOSITE')).not.toBeInTheDocument();
    });

    it('8. ignores legacy localStorage favorites like REST_COMPOSITE without crashing', () => {
        const favoritesKey = 'dentix_chart_favorites_101_42';
        localStorage.setItem(favoritesKey, JSON.stringify(['REST_COMPOSITE', 'ENDO_RCT', 'CARIES']));

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={mockClinicProcedures}
            />
        );

        // CARIES is a known key and renders; legacy procedure codes are ignored safely
        expect(screen.getByTestId('chart-quick-action-item-CARIES')).toBeInTheDocument();
        // Favorites container only has CARIES (legacy codes ignored)
        const favoritesSection = screen.getByTestId('chart-quick-action-favorites');
        expect(favoritesSection.querySelectorAll('[data-testid^="chart-quick-action-item-"]').length).toBe(1);
    });

    it('9. renders skeleton when loading and empty state when clinic procedures are empty (no fallback to fake catalog)', () => {
        const { rerender } = render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={[]}
                isLoading={true}
            />
        );

        // Loading state
        expect(screen.getByTestId('chart-quick-action-loading')).toBeInTheDocument();

        // Loaded empty state
        rerender(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={[]}
                isLoading={false}
            />
        );

        expect(screen.getByTestId('no-clinic-procedures-hint')).toBeInTheDocument();
        expect(screen.getByText(/No clinic procedures configured/i)).toBeInTheDocument();
        expect(screen.getByText(/Settings → Procedures/i)).toBeInTheDocument();
        // Never falls back to fake canonical procedures
        expect(screen.queryByTestId('chart-quick-action-item-REST_COMPOSITE')).not.toBeInTheDocument();
    });

    it('10. renders expander button when clinic procedures exceed 8', () => {
        const tenProcedures = Array.from({ length: 10 }, (_, i) => ({
            id: i + 1,
            name: `Procedure ${i + 1}`,
            canonical_code: null,
            price: 100 * (i + 1),
            category: 'clinic',
        }));

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
                clinicProcedures={tenProcedures}
            />
        );

        // Button "Show all (10)" is visible
        const expandBtn = screen.getByTestId('show-all-procedures-button');
        expect(expandBtn).toBeInTheDocument();
        expect(expandBtn).toHaveTextContent(/Show all \(10\)/i);

        // Click to expand
        fireEvent.click(expandBtn);
        expect(expandBtn).toHaveTextContent(/Show less/i);
        expect(screen.getByTestId('chart-quick-action-item-proc:10')).toBeInTheDocument();
    });
});
