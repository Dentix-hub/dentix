import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const srcRoot = path.resolve(process.cwd(), 'src');
const strict = process.argv.includes('--strict');

const rules = [
  {
    id: 'arbitrary-z-index',
    message: 'Use the canonical z-layer scale instead of arbitrary z-[…].',
    pattern: /\bz-\[[^\]]+\]/g,
  },
  {
    id: 'arbitrary-radius',
    message: 'Use radius-control/card/overlay/pill instead of rounded-[…].',
    pattern: /\brounded-\[[^\]]+\]/g,
  },
  {
    id: 'arbitrary-shadow',
    message: 'Use shadow-low/medium/high instead of shadow-[…].',
    pattern: /\bshadow-\[[^\]]+\]/g,
  },
  {
    id: 'raw-portal',
    message: 'Feature code should consume Dentix overlay primitives instead of createPortal directly.',
    pattern: /\bcreatePortal\s*\(/g,
    outsideSharedUiOnly: true,
  },
  {
    id: 'raw-fullscreen-overlay',
    message: 'Feature-local fixed inset-0 overlays should migrate behind the Dentix overlay contract.',
    pattern: /(?:className|class)\s*=\s*["'`][^"'`]*\bfixed\b[^"'`]*\binset-0\b/g,
    outsideSharedUiOnly: true,
  },
  {
    id: 'direct-overlay-library-import',
    message: 'External overlay libraries belong behind frontend/src/shared/ui wrappers.',
    pattern: /from\s+["'](?:@radix-ui\/react-(?:dialog|dropdown-menu|select|tooltip)|@headlessui\/react)["']/g,
    outsideSharedUiOnly: true,
  },
];

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...await walk(full));
    else if (/\.(?:js|jsx|ts|tsx)$/.test(entry.name)) files.push(full);
  }
  return files;
}

function lineFor(text, index) {
  return text.slice(0, index).split('\n').length;
}

const files = await walk(srcRoot);
const findings = [];

for (const file of files) {
  const rel = path.relative(process.cwd(), file).replaceAll(path.sep, '/');
  const inSharedUi = rel.startsWith('src/shared/ui/');
  const text = await readFile(file, 'utf8');

  for (const rule of rules) {
    if (rule.outsideSharedUiOnly && inSharedUi) continue;
    rule.pattern.lastIndex = 0;
    for (const match of text.matchAll(rule.pattern)) {
      findings.push({
        rule: rule.id,
        message: rule.message,
        file: rel,
        line: lineFor(text, match.index ?? 0),
        sample: match[0].replace(/\s+/g, ' ').slice(0, 120),
      });
    }
  }
}

const grouped = new Map();
for (const finding of findings) {
  if (!grouped.has(finding.rule)) grouped.set(finding.rule, []);
  grouped.get(finding.rule).push(finding);
}

console.log('Dentix Design System guardrail report');
console.log(`Mode: ${strict ? 'strict' : 'report-only'}`);
console.log(`Scanned ${files.length} source files; found ${findings.length} legacy violations.`);

for (const rule of rules) {
  const items = grouped.get(rule.id) ?? [];
  console.log(`\n[${rule.id}] ${items.length} — ${rule.message}`);
  for (const item of items.slice(0, 20)) {
    console.log(`  ${item.file}:${item.line}  ${item.sample}`);
  }
  if (items.length > 20) console.log(`  … ${items.length - 20} more`);
}

if (!strict) {
  console.log('\nReport-only rollout: legacy findings do not fail CI. Use --strict only after a checked baseline/new-violation gate is introduced.');
  process.exit(0);
}

if (findings.length > 0) {
  console.error('\nStrict guardrails failed. Migrate or baseline legacy violations before enabling strict mode in CI.');
  process.exit(1);
}
