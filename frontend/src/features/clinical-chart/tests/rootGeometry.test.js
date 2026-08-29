import { describe, expect, it } from 'vitest';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import {
    ROOT_OUTLINE_REGISTRY,
    ROOT_STYLE_TOKENS,
    ROOT_VIEW_BOX,
    getRootGeometry,
} from '../rendering/rootGeometry';

describe('root anatomy geometry', () => {
    it('resolves every anatomy root reference to a non-empty SVG path', () => {
        Object.values(DENTAL_ANATOMY_REGISTRY).forEach((anatomy) => {
            const roots = getRootGeometry(anatomy.toothKey);
            expect(roots).toHaveLength(anatomy.rootCount);
            roots.forEach((root) => {
                expect(root.toothKey).toBe(anatomy.toothKey);
                expect(root.path).toMatch(/^M.* Z$/);
                expect(root.path).not.toMatch(/NaN|undefined|Infinity/);
                expect(root.viewBox).toBe(ROOT_VIEW_BOX);
                expect(root.cervicalAnchors.left.y).toBe(0);
                expect(root.cervicalAnchors.right.y).toBe(0);
                expect(root.cervicalAnchors.left.x).toBeLessThan(root.cervicalAnchors.right.x);
                expect(root.apexAnchor.y).toBeGreaterThan(30);
                expect(root.apexAnchor.y).toBeLessThan(48);
            });
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
        expect(ROOT_STYLE_TOKENS).toEqual({ fill: '#ffffff', stroke: '#94a3b8', strokeWidth: 1.5 });
    });

    it('stores a separate root record for each FDI tooth instead of sharing a family outline', () => {
        const outlines = Object.values(ROOT_OUTLINE_REGISTRY);

        expect(new Set(outlines.map((root) => root.outlineRef)).size).toBe(outlines.length);
        expect(outlines.every((root) => root.outlineRef.startsWith(`root:${root.toothKey}:`))).toBe(true);
    });

    it('keeps primary molar roots more divergent to reserve the successor space', () => {
        const primaryUpperMolar = getRootGeometry('55');
        const primaryLowerMolar = getRootGeometry('85');

        expect(Math.min(...primaryUpperMolar.map((root) => root.apexAnchor.x))).toBeLessThan(5);
        expect(Math.max(...primaryUpperMolar.map((root) => root.apexAnchor.x))).toBeGreaterThan(45);
        expect(Math.min(...primaryLowerMolar.map((root) => root.apexAnchor.x))).toBeLessThan(5);
        expect(Math.max(...primaryLowerMolar.map((root) => root.apexAnchor.x))).toBeGreaterThan(45);
    });
});
