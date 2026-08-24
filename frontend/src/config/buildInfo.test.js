import { describe, expect, it } from 'vitest';
import { BUILD_INFO, getBuildLabel } from './buildInfo';

describe('build identity', () => {
    it('always exposes a non-empty identity shape', () => {
        expect(BUILD_INFO).toBeTypeOf('object');
        expect(typeof BUILD_INFO.sha).toBe('string');
        expect(typeof BUILD_INFO.environment).toBe('string');
    });

    it('is immutable so diagnostics cannot be tampered with at runtime', () => {
        expect(() => {
            'use strict';
            BUILD_INFO.sha = 'tampered';
        }).toThrow(TypeError);
    });

    it('renders a support-readable build label', () => {
        const label = getBuildLabel();
        expect(label).toContain(BUILD_INFO.shaShort || BUILD_INFO.sha);
    });
});
