import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdtemp, readFile, stat, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(scriptDir, '..');
const mainSourcePath = path.join(frontendRoot, 'src', 'main.jsx');
const tempRoot = await mkdtemp(path.join(os.tmpdir(), 'dentix-stale-deployment-'));
const distA = path.join(tempRoot, 'dist-a');
const distB = path.join(tempRoot, 'dist-b');

function runBuild(outDir) {
  execFileSync(
    'npm',
    ['run', 'build', '--', '--outDir', outDir, '--emptyOutDir'],
    {
      cwd: frontendRoot,
      env: process.env,
      stdio: 'inherit',
    },
  );
}

function extractModuleEntry(html) {
  const scriptTags = html.match(/<script\b[^>]*>/g) ?? [];
  for (const tag of scriptTags) {
    if (!/type=["']module["']/.test(tag)) continue;
    const srcMatch = tag.match(/src=["']([^"']+)["']/);
    if (srcMatch?.[1]?.startsWith('/assets/') && srcMatch[1].endsWith('.js')) {
      return srcMatch[1];
    }
  }
  throw new Error('Unable to find the Vite module entry in dist/index.html');
}

async function fileExists(filePath) {
  try {
    await stat(filePath);
    return true;
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    throw error;
  }
}

async function startStaticServer(rootDir) {
  const resolvedRoot = path.resolve(rootDir);
  const server = createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url ?? '/', 'http://127.0.0.1');
      const relativePath = decodeURIComponent(requestUrl.pathname).replace(/^\/+/, '') || 'index.html';
      const candidate = path.resolve(resolvedRoot, relativePath);

      if (candidate !== resolvedRoot && !candidate.startsWith(`${resolvedRoot}${path.sep}`)) {
        response.statusCode = 400;
        response.end('bad path');
        return;
      }

      if (!(await fileExists(candidate)) || (await stat(candidate)).isDirectory()) {
        response.statusCode = 404;
        response.end('not found');
        return;
      }

      response.statusCode = 200;
      response.end(await readFile(candidate));
    } catch (error) {
      response.statusCode = 500;
      response.end(String(error));
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });

  const address = server.address();
  if (!address || typeof address === 'string') {
    server.close();
    throw new Error('Unable to resolve the temporary static-server port');
  }

  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
  };
}

const originalMainSource = await readFile(mainSourcePath, 'utf8');

try {
  runBuild(distA);

  // Change real application entry code only inside this disposable CI checkout so
  // Vite must emit a distinct Version B entry hash. The source is restored below.
  await writeFile(
    mainSourcePath,
    `${originalMainSource}\nwindow.__DENTIX_PHASE5_BUILD_MARKER__ = 'version-b';\n`,
    'utf8',
  );
  runBuild(distB);
} finally {
  await writeFile(mainSourcePath, originalMainSource, 'utf8');
}

const htmlA = await readFile(path.join(distA, 'index.html'), 'utf8');
const htmlB = await readFile(path.join(distB, 'index.html'), 'utf8');
const entryA = extractModuleEntry(htmlA);
const entryB = extractModuleEntry(htmlB);

if (entryA === entryB) {
  throw new Error(`Version A and Version B unexpectedly share the same entry asset: ${entryA}`);
}

const entryAOnB = path.join(distB, entryA.replace(/^\/+/, ''));
const entryBOnB = path.join(distB, entryB.replace(/^\/+/, ''));

if (await fileExists(entryAOnB)) {
  throw new Error(`Version B unexpectedly retained Version A entry asset: ${entryA}`);
}
if (!(await fileExists(entryBOnB))) {
  throw new Error(`Version B is missing its own entry asset: ${entryB}`);
}

const swB = await readFile(path.join(distB, 'sw.js'), 'utf8');
const entryABasename = path.basename(entryA);
const entryBBasename = path.basename(entryB);
if (!swB.includes(entryBBasename)) {
  throw new Error(`Version B service worker does not precache its current entry asset: ${entryBBasename}`);
}
if (swB.includes(entryABasename)) {
  throw new Error(`Version B service worker still references stale Version A entry asset: ${entryABasename}`);
}

const staticServer = await startStaticServer(distB);
try {
  const staleResponse = await fetch(`${staticServer.baseUrl}${entryA}`);
  if (staleResponse.status !== 404) {
    throw new Error(`Expected stale Version A asset to return 404 from Version B, got ${staleResponse.status}`);
  }

  const currentResponse = await fetch(`${staticServer.baseUrl}${entryB}`);
  if (currentResponse.status !== 200) {
    throw new Error(`Expected current Version B asset to return 200, got ${currentResponse.status}`);
  }
} finally {
  await staticServer.close();
}

console.log('Stale deployment reproduction passed.');
console.log(`Version A entry: ${entryA}`);
console.log(`Version B entry: ${entryB}`);
console.log('Version A asset returns 404 on Version B, while Version B asset returns 200.');
console.log('Version B service worker precaches the current entry and excludes the stale Version A entry.');
