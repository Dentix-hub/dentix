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

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'en' },
    }),
}));

import { useAuthStore } from '@/store/auth.store';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
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

describe('G8-M02, G8-M08, G8-M09, G8-M10: ChartQuickActionLauncher UI & Interactions', () => {
    beforeEach(() => {
        localStorage.clear();
        useAuthStore.setState({ user: { id: 42, tenant_id: 101, role: 'doctor' } });
    });

    it('renders default favorites and active tooth badge when a tooth is selected', () => {
        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
            />
        );

        expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-search')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-favorites')).toBeInTheDocument();

        // Default favorites
        expect(screen.getByTestId('chart-quick-action-item-REST_COMPOSITE')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-ENDO_RCT')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-PROS_CROWN')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-SURG_EXTRACTION')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-CARIES')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-FRACTURE')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-item-PAIN')).toBeInTheDocument();
    });

    it('renders recents section when items are saved in localStorage under tenant/user-scoped key', () => {
        const recentsKey = 'dentix_chart_recents_101_42';
        localStorage.setItem(recentsKey, JSON.stringify(['ENDO_RCT', 'PROS_CROWN']));

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
            />
        );

        expect(screen.getByTestId('chart-quick-action-recents')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-recent-item-ENDO_RCT')).toBeInTheDocument();
    });

    it('filters items in real time when searching in English and Arabic', () => {
        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
            />
        );

        const searchInput = screen.getByTestId('chart-quick-action-search');

        // Search English
        fireEvent.change(searchInput, { target: { value: 'composite' } });
        expect(screen.getByTestId('chart-quick-action-item-REST_COMPOSITE')).toBeInTheDocument();
        expect(screen.queryByTestId('chart-quick-action-item-ENDO_RCT')).not.toBeInTheDocument();

        // Search Arabic
        fireEvent.change(searchInput, { target: { value: 'جذور' } });
        expect(screen.getByTestId('chart-quick-action-item-ENDO_RCT')).toBeInTheDocument();
        expect(screen.queryByTestId('chart-quick-action-item-REST_COMPOSITE')).not.toBeInTheDocument();

        // Search non-existing
        fireEvent.change(searchInput, { target: { value: 'xyzunknown' } });
        expect(screen.getByTestId('no-actions-found')).toBeInTheDocument();
    });

    it('stars and unstars actions, updating favorites in localStorage', () => {
        const favoritesKey = 'dentix_chart_favorites_101_42';

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={vi.fn()}
            />
        );

        // Search for composite so the card stays rendered in search results even when unstarred
        const searchInput = screen.getByTestId('chart-quick-action-search');
        fireEvent.change(searchInput, { target: { value: 'composite' } });

        const favToggle = screen.getByTestId('favorite-toggle-REST_COMPOSITE');
        fireEvent.click(favToggle);

        // Should be removed from favorites
        const stored = JSON.parse(localStorage.getItem(favoritesKey) || '[]');
        expect(stored.includes('REST_COMPOSITE')).toBe(false);

        // Click again to re-add
        fireEvent.click(favToggle);
        const storedAfter = JSON.parse(localStorage.getItem(favoritesKey) || '[]');
        expect(storedAfter.includes('REST_COMPOSITE')).toBe(true);
    });

    it('executes a whole-tooth action immediately, updating recents in localStorage', () => {
        const onAction = vi.fn();
        const recentsKey = 'dentix_chart_recents_101_42';

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={onAction}
            />
        );

        const extractionItem = screen.getByTestId('chart-quick-action-item-SURG_EXTRACTION');
        fireEvent.click(extractionItem);

        expect(onAction).toHaveBeenCalledWith(
            expect.objectContaining({
                item: expect.objectContaining({ code: 'SURG_EXTRACTION' }),
                toothKeys: ['16'],
                targetKind: 'tooth',
                surfaces: [],
            })
        );

        // Recents updated in localStorage
        const storedRecents = JSON.parse(localStorage.getItem(recentsKey) || '[]');
        expect(storedRecents[0]).toBe('SURG_EXTRACTION');
    });

    it('opens surface prompt for surface-capable action when no surface was pre-selected, pre-selecting smart default', () => {
        const onAction = vi.fn();

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={onAction}
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
                item: expect.objectContaining({ code: 'REST_COMPOSITE' }),
                toothKeys: ['16'],
                targetKind: 'surface',
                surfaces: expect.arrayContaining(['O', 'M']),
            })
        );
    });
});
