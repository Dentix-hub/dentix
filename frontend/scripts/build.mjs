#!/usr/bin/env node
/**
 * build.mjs
 * Build runner for Dentix frontend.
 * Executes Vite build forwarding all CLI arguments (such as --outDir, --emptyOutDir),
 * then automatically verifies marketing & discovery artifacts on the target output directory.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runVerification } from './verify-marketing-artifacts.mjs';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(scriptDir, '..');

const args = process.argv.slice(2);
const isWindows = process.platform === 'win32';

// 1. Forward all CLI arguments to Vite build
const viteCmd = isWindows ? 'npx.cmd' : 'npx';
const viteResult = spawnSync(viteCmd, ['vite', 'build', ...args], {
  cwd: frontendRoot,
  stdio: 'inherit',
  shell: isWindows,
  env: process.env,
});

if (viteResult.status !== 0) {
  process.exit(viteResult.status ?? 1);
}

// 2. Identify target output directory
let outDir = 'dist';
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--outDir' && args[i + 1]) {
    outDir = args[i + 1];
    break;
  } else if (args[i].startsWith('--outDir=')) {
    outDir = args[i].slice('--outDir='.length);
    break;
  }
}

const resolvedOutDir = path.isAbsolute(outDir)
  ? outDir
  : path.resolve(frontendRoot, outDir);

// 3. Verify marketing artifacts against the output directory
runVerification(resolvedOutDir);
