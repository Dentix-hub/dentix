import { describe, it, expect } from 'vitest';
import { resolveBuildInfo } from '../../buildInfoResolver.js';

describe('resolveBuildInfo', () => {
    it('resolves SHA and environment from build-info.json if present', () => {
        const result = resolveBuildInfo('production', {
            fileBuildInfo: { sha: 'abcdef1234567890', environment: 'staging' },
            env: { BUILD_SHA: 'ignored', VITE_ENVIRONMENT: 'ignored' },
        });

        expect(result.sha).toBe('abcdef1234567890');
        expect(result.shaShort).toBe('abcdef1');
        expect(result.environment).toBe('staging');
    });

    it('falls back to BUILD_SHA and VITE_ENVIRONMENT if build-info.json is missing or empty', () => {
        const result = resolveBuildInfo('production', {
            fileBuildInfo: null,
            env: { BUILD_SHA: '1122334455667788', VITE_ENVIRONMENT: 'staging' },
        });

        expect(result.sha).toBe('1122334455667788');
        expect(result.shaShort).toBe('1122334');
        expect(result.environment).toBe('staging');
    });

    it('falls back to git when no build-info.json or env is provided', () => {
        const result = resolveBuildInfo('production', {
            fileBuildInfo: null,
            env: {},
            execGit: () => 'gitcommit987654321',
        });

        expect(result.sha).toBe('gitcommit987654321');
        expect(result.shaShort).toBe('gitcomm');
        expect(result.environment).toBe('production');
    });

    it('falls back to unknown and mode when git fails and no other sources exist', () => {
        const result = resolveBuildInfo('development', {
            fileBuildInfo: null,
            env: {},
            execGit: () => null,
        });

        expect(result.sha).toBe('unknown');
        expect(result.shaShort).toBe('unknown');
        expect(result.environment).toBe('development');
    });
});
