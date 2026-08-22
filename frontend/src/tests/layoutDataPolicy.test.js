import { describe, expect, it } from 'vitest';

import { shouldLoadCommandPaletteData } from '@/layouts/layoutDataPolicy';

describe('layout data loading policy', () => {
    it('does not load patients and appointments during ordinary page navigation', () => {
        expect(shouldLoadCommandPaletteData({ isOpen: false, isSuperAdmin: false })).toBe(false);
    });

    it('loads command palette data only while a clinic user opens it', () => {
        expect(shouldLoadCommandPaletteData({ isOpen: true, isSuperAdmin: false })).toBe(true);
        expect(shouldLoadCommandPaletteData({ isOpen: true, isSuperAdmin: true })).toBe(false);
    });
});
