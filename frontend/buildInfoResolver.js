/* eslint-env node */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

/**
 * Pure resolver for build info.
 * Resolution precedence:
 * SHA: build-info.json -> env.BUILD_SHA -> git rev-parse HEAD -> 'unknown'
 * Environment: build-info.json -> env.VITE_ENVIRONMENT -> mode -> 'development'
 */
export function resolveBuildInfo(mode, options = {}) {
    const cwd = options.cwd || process.cwd();
    const env = options.env || process.env;

    let fileBuildInfo = options.fileBuildInfo;
    if (fileBuildInfo === undefined) {
        try {
            const buildInfoPath = options.buildInfoPath || path.resolve(cwd, 'build-info.json');
            if (fs.existsSync(buildInfoPath)) {
                fileBuildInfo = JSON.parse(fs.readFileSync(buildInfoPath, 'utf8'));
            }
        } catch {
            fileBuildInfo = null;
        }
    }

    // SHA order: build-info.json -> env.BUILD_SHA -> git -> 'unknown'
    let sha = fileBuildInfo?.sha || env?.BUILD_SHA || null;
    if (!sha) {
        if (typeof options.execGit === 'function') {
            sha = options.execGit() || null;
        } else {
            try {
                sha = execSync('git rev-parse HEAD', { cwd, encoding: 'utf8' }).trim();
            } catch {
                sha = null;
            }
        }
    }
    sha = sha || 'unknown';

    // Environment order: build-info.json -> env.VITE_ENVIRONMENT -> mode -> 'development'
    const environment = fileBuildInfo?.environment || env?.VITE_ENVIRONMENT || mode || 'development';

    return {
        sha,
        shaShort: sha === 'unknown' ? 'unknown' : sha.slice(0, 7),
        builtAt: new Date().toISOString(),
        environment,
    };
}
