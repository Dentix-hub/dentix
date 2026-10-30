import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parse } from '@babel/parser';
import traverseModule from '@babel/traverse';

const traverse = traverseModule.default || traverseModule;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function flattenTranslations(obj, prefix = '') {
    const result = {};
    for (const key of Object.keys(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;
        const val = obj[key];
        if (val && typeof val === 'object' && !Array.isArray(val)) {
            Object.assign(result, flattenTranslations(val, fullKey));
        } else {
            result[fullKey] = val;
        }
    }
    return result;
}

export function findSourceFiles(dir, fileList = []) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            if (
                entry.name !== 'node_modules' &&
                entry.name !== '__tests__' &&
                entry.name !== 'locales' &&
                entry.name !== 'dist' &&
                entry.name !== 'build'
            ) {
                findSourceFiles(fullPath, fileList);
            }
        } else if (
            entry.isFile() &&
            (entry.name.endsWith('.js') || entry.name.endsWith('.jsx')) &&
            !entry.name.endsWith('.test.js') &&
            !entry.name.endsWith('.test.jsx') &&
            !entry.name.endsWith('.spec.js') &&
            !entry.name.endsWith('.spec.jsx')
        ) {
            fileList.push(fullPath);
        }
    }
    return fileList;
}

export function extractKeysFromAst(code, filePath) {
    const staticCalls = [];
    const dynamicCalls = [];

    let ast;
    try {
        ast = parse(code, {
            sourceType: 'module',
            plugins: ['jsx', 'typescript'],
            errorRecovery: true,
        });
    } catch (e) {
        console.error(`Failed parsing ${filePath}:`, e.message);
        return { staticCalls, dynamicCalls };
    }

    traverse(ast, {
        CallExpression({ node }) {
            const callee = node.callee;
            let isTCall = false;

            // t(...)
            if (callee.type === 'Identifier' && callee.name === 't') {
                isTCall = true;
            }
            // i18n.t(...)
            else if (
                callee.type === 'MemberExpression' &&
                callee.property.type === 'Identifier' &&
                callee.property.name === 't'
            ) {
                isTCall = true;
            }

            if (!isTCall || node.arguments.length === 0) return;

            const firstArg = node.arguments[0];
            const secondArg = node.arguments[1];

            let defaultText = null;
            if (secondArg) {
                if (secondArg.type === 'StringLiteral') {
                    defaultText = secondArg.value;
                } else if (
                    secondArg.type === 'TemplateLiteral' &&
                    secondArg.expressions.length === 0 &&
                    secondArg.quasis.length === 1
                ) {
                    defaultText = secondArg.quasis[0].value.raw;
                } else if (secondArg.type === 'ObjectExpression') {
                    for (const prop of secondArg.properties) {
                        if (
                            prop.type === 'ObjectProperty' &&
                            prop.key.type === 'Identifier' &&
                            prop.key.name === 'defaultValue' &&
                            prop.value.type === 'StringLiteral'
                        ) {
                            defaultText = prop.value.value;
                        }
                    }
                }
            }

            // Static string literal
            if (firstArg.type === 'StringLiteral') {
                staticCalls.push({
                    key: firstArg.value,
                    file: filePath,
                    loc: firstArg.loc?.start,
                    defaultText,
                });
            }
            // Static template literal without expressions: `some.key`
            else if (
                firstArg.type === 'TemplateLiteral' &&
                firstArg.expressions.length === 0 &&
                firstArg.quasis.length === 1
            ) {
                staticCalls.push({
                    key: firstArg.quasis[0].value.raw,
                    file: filePath,
                    loc: firstArg.loc?.start,
                    defaultText,
                });
            }
            // Dynamic expression
            else {
                let rawExpr = 'dynamic_expression';
                if (firstArg.type === 'TemplateLiteral') {
                    rawExpr = firstArg.quasis.map((q) => q.value.raw).join('${...}');
                } else if (firstArg.type === 'Identifier') {
                    rawExpr = firstArg.name;
                } else if (firstArg.type === 'MemberExpression') {
                    rawExpr = 'member_expression';
                }
                dynamicCalls.push({
                    expression: rawExpr,
                    file: filePath,
                    loc: firstArg.loc?.start,
                });
            }
        },
    });

    return { staticCalls, dynamicCalls };
}

export function extractI18nKeys(options = {}) {
    const rootDir = options.rootDir || path.resolve(__dirname, '..');
    const srcDir = options.srcDir || path.join(rootDir, 'src');
    const arPath =
        options.arPath || path.join(srcDir, 'locales', 'ar', 'translation.json');
    const enPath =
        options.enPath || path.join(srcDir, 'locales', 'en', 'translation.json');

    const arJson = JSON.parse(fs.readFileSync(arPath, 'utf8'));
    const enJson = JSON.parse(fs.readFileSync(enPath, 'utf8'));

    const arFlat = flattenTranslations(arJson);
    const enFlat = flattenTranslations(enJson);

    const sourceFiles = findSourceFiles(srcDir);
    const staticMap = new Map(); // key -> { key, occurrences: [], defaultText: null }
    const dynamicCalls = [];

    for (const file of sourceFiles) {
        const content = fs.readFileSync(file, 'utf8');
        const { staticCalls, dynamicCalls: fileDynamic } = extractKeysFromAst(
            content,
            file
        );

        for (const item of staticCalls) {
            const trimmedKey = item.key.trim();
            if (!trimmedKey) continue;

            if (!staticMap.has(trimmedKey)) {
                staticMap.set(trimmedKey, {
                    key: trimmedKey,
                    occurrences: [{ file: item.file, loc: item.loc }],
                    defaultText: item.defaultText,
                });
            } else {
                const existing = staticMap.get(trimmedKey);
                existing.occurrences.push({ file: item.file, loc: item.loc });
                if (!existing.defaultText && item.defaultText) {
                    existing.defaultText = item.defaultText;
                }
            }
        }

        dynamicCalls.push(...fileDynamic);
    }

    const staticKeys = Array.from(staticMap.values());

    const missingInAr = [];
    const missingInEn = [];
    const missingInBoth = [];

    for (const item of staticKeys) {
        const inAr = item.key in arFlat;
        const inEn = item.key in enFlat;

        if (!inAr && !inEn) {
            missingInBoth.push(item);
        } else if (!inAr) {
            missingInAr.push(item);
        } else if (!inEn) {
            missingInEn.push(item);
        }
    }

    const enMissingInAr = Object.keys(enFlat).filter((k) => !(k in arFlat));
    const arMissingInEn = Object.keys(arFlat).filter((k) => !(k in enFlat));

    return {
        totalStaticKeys: staticKeys.length,
        totalDynamicCalls: dynamicCalls.length,
        arTotalKeys: Object.keys(arFlat).length,
        enTotalKeys: Object.keys(enFlat).length,
        staticKeys,
        dynamicCalls,
        missingInBoth,
        missingInAr,
        missingInEn,
        enMissingInAr,
        arMissingInEn,
        arFlat,
        enFlat,
    };
}

if (process.argv[1] === __filename) {
    const report = extractI18nKeys();
    console.log('=== DENTIX I18N EXTRACTION REPORT ===');
    console.log(`Source static t() keys: ${report.totalStaticKeys}`);
    console.log(`Source dynamic t() calls: ${report.totalDynamicCalls}`);
    console.log(`AR translation keys: ${report.arTotalKeys}`);
    console.log(`EN translation keys: ${report.enTotalKeys}`);
    console.log(`Missing in BOTH ar and en: ${report.missingInBoth.length}`);
    console.log(`Missing in AR only: ${report.missingInAr.length}`);
    console.log(`Missing in EN only: ${report.missingInEn.length}`);
    console.log(`Keys in EN missing in AR: ${report.enMissingInAr.length}`);
    console.log(`Keys in AR missing in EN: ${report.arMissingInEn.length}`);

    if (process.argv.includes('--verbose')) {
        console.log('\n--- Missing in BOTH ar & en ---');
        for (const item of report.missingInBoth) {
            const files = [...new Set(item.occurrences.map((o) => path.basename(o.file)))].join(', ');
            console.log(`  ${item.key} (default: "${item.defaultText || ''}") in [${files}]`);
        }

        console.log('\n--- Missing in AR only ---');
        for (const item of report.missingInAr) {
            console.log(`  ${item.key}`);
        }

        console.log('\n--- Keys in EN missing in AR ---');
        for (const k of report.enMissingInAr) {
            console.log(`  ${k}`);
        }

        console.log('\n--- Keys in AR missing in EN ---');
        for (const k of report.arMissingInEn) {
            console.log(`  ${k}`);
        }

        console.log('\n--- Dynamic Calls ---');
        for (const d of report.dynamicCalls.slice(0, 30)) {
            console.log(`  ${d.expression} (${path.basename(d.file)})`);
        }
    }
}
