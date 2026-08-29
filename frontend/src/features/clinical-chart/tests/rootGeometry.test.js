import { describe, expect, it } from 'vitest';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import { ROOT_OUTLINE_REGISTRY, ROOT_STYLE_TOKENS, getRootGeometry } from '../rendering/rootGeometry';

describe('root anatomy geometry', () => {
    it('resolves every anatomy root reference to a non-empty SVG path', () => {
        Object.values(DENTAL_ANATOMY_REGISTRY).forEach((anatomy) => {
            const roots = getRootGeometry(anatomy.toothKey);
            expect(roots).toHaveLength(anatomy.rootCount);
            expect(roots.every((root) => root?.path?.startsWith('M'))).toBe(true);
        });
    });

    it.each([
        ['11', 1], ['14', 2], ['16', 3], ['34', 1], ['36', 2],
        ['51', 1], ['65', 3], ['75', 2],
    ])('uses the expected root family for FDI %s', (toothKey, count) => {
        expect(getRootGeometry(toothKey)).toHaveLength(count);
    });

    it('uses the same restrained outline language across every root', () => {
        expect(new Set(Object.values(ROOT_OUTLINE_REGISTRY).map((root) => root.style))).toEqual(new Set([ROOT_STYLE_TOKENS]));
        expect(ROOT_STYLE_TOKENS).toEqual({ fill: '#f8fafc', stroke: '#94a3b8', strokeWidth: 1.5 });
    });
});

