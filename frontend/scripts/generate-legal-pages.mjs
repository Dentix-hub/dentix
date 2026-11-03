#!/usr/bin/env node
/**
 * generate-legal-pages.mjs
 * Generates static HTML pages for Privacy Policy and Terms of Service in both
 * Arabic and English directly from the authoritative translation source:
 * frontend/src/locales/{ar,en}/translation.json.
 *
 * Guarantees:
 * - Single source of truth (zero duplicate manual legal text).
 * - Exact wording and structure preserved.
 * - Semantic HTML, accessible headings, responsive layout.
 * - Proper HTML lang/dir, canonical, reciprocal hreflang, structured data.
 * - Zero executable JavaScript.
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function loadLocales() {
  const arPath = path.join(frontendRoot, 'src/locales/ar/translation.json');
  const enPath = path.join(frontendRoot, 'src/locales/en/translation.json');

  const ar = JSON.parse(readFileSync(arPath, 'utf8'));
  const en = JSON.parse(readFileSync(enPath, 'utf8'));

  return { ar, en };
}

function renderPrivacyBody(data, lang) {
  const sections = data.sections || {};
  let html = '';

  const sortedKeys = Object.keys(sections).sort((a, b) => Number(a) - Number(b));

  for (const key of sortedKeys) {
    const s = sections[key];
    html += `      <section class="prose-section" id="section-${key}">\n`;
    if (s.title) {
      html += `        <h2>${escapeHtml(s.title)}</h2>\n`;
    }
    if (s.intro) {
      html += `        <p>${escapeHtml(s.intro)}</p>\n`;
    }
    if (s.clinic) {
      html += `        <div class="prose-subblock">\n`;
      html += `          <h3>${escapeHtml(s.clinic.title)}</h3>\n`;
      if (Array.isArray(s.clinic.items)) {
        html += `          <ul class="prose-list">\n`;
        for (const item of s.clinic.items) {
          html += `            <li>${escapeHtml(item)}</li>\n`;
        }
        html += `          </ul>\n`;
      }
      html += `        </div>\n`;
    }
    if (s.users) {
      html += `        <div class="prose-subblock">\n`;
      html += `          <h3>${escapeHtml(s.users.title)}</h3>\n`;
      if (Array.isArray(s.users.items)) {
        html += `          <ul class="prose-list">\n`;
        for (const item of s.users.items) {
          html += `            <li>${escapeHtml(item)}</li>\n`;
        }
        html += `          </ul>\n`;
      }
      html += `        </div>\n`;
    }
    if (s.patients) {
      html += `        <div class="prose-subblock">\n`;
      html += `          <h3>${escapeHtml(s.patients.title)}</h3>\n`;
      if (Array.isArray(s.patients.items)) {
        html += `          <ul class="prose-list">\n`;
        for (const item of s.patients.items) {
          html += `            <li>${escapeHtml(item)}</li>\n`;
        }
        html += `          </ul>\n`;
      }
      html += `        </div>\n`;
    }
    if (Array.isArray(s.items)) {
      html += `        <ul class="prose-list">\n`;
      for (const item of s.items) {
        html += `          <li>${escapeHtml(item)}</li>\n`;
      }
      html += `        </ul>\n`;
    }
    if (s.content) {
      html += `        <p>${escapeHtml(s.content)}</p>\n`;
    }
    if (s.alert) {
      html += `        <div class="prose-alert">${escapeHtml(s.alert)}</div>\n`;
    }
    if (s.outro) {
      html += `        <p>${escapeHtml(s.outro)}</p>\n`;
    }
    html += `      </section>\n`;
  }

  return html;
}

function renderTermsBody(data, lang) {
  const sections = data.sections || {};
  let html = '';

  const sortedKeys = Object.keys(sections).sort((a, b) => Number(a) - Number(b));

  for (const key of sortedKeys) {
    const s = sections[key];
    html += `      <section class="prose-section" id="section-${key}">\n`;
    if (s.title) {
      html += `        <h2>${escapeHtml(s.title)}</h2>\n`;
    }
    if (s.intro) {
      html += `        <p>${escapeHtml(s.intro)}</p>\n`;
    }
    if (s.content) {
      html += `        <p>${escapeHtml(s.content)}</p>\n`;
    }
    if (Array.isArray(s.items)) {
      html += `        <ul class="prose-list">\n`;
      for (const item of s.items) {
        html += `          <li>${escapeHtml(item)}</li>\n`;
      }
      html += `        </ul>\n`;
    }
    if (s.outro) {
      html += `        <p>${escapeHtml(s.outro)}</p>\n`;
    }
    html += `      </section>\n`;
  }

  return html;
}

function generateLegalHtml({
  lang,
  dir,
  pageType, // 'privacy' | 'terms'
  data,
  pageTitle,
  metaDescription,
  canonicalUrl,
  hreflangAr,
  hreflangEn,
  hreflangDefault,
  targetLangUrl,
  targetLangText,
  targetLangAria,
  targetLangCode,
}) {
  const isAr = lang === 'ar';
  const homeUrl = isAr ? '/ar' : '/en';
  const termsUrl = isAr ? '/ar/terms' : '/en/terms';
  const privacyUrl = isAr ? '/ar/privacy' : '/en/privacy';
  const breadcrumbName = isAr ? (pageType === 'privacy' ? 'سياسة الخصوصية' : 'الشروط والأحكام') : (pageType === 'privacy' ? 'Privacy Policy' : 'Terms of Service');
  const homeBreadcrumb = isAr ? 'الرئيسية' : 'Home';

  const bodyContent = pageType === 'privacy'
    ? renderPrivacyBody(data, lang)
    : renderTermsBody(data, lang);

  const structuredData = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': 'https://www.dentixs.app/#organization',
        'name': 'Dentix',
        'url': 'https://www.dentixs.app',
        'logo': 'https://www.dentixs.app/logo.webp',
      },
      {
        '@type': 'WebPage',
        '@id': `${canonicalUrl}#webpage`,
        'url': canonicalUrl,
        'name': pageTitle,
        'inLanguage': lang,
        'isPartOf': {
          '@type': 'WebSite',
          '@id': 'https://www.dentixs.app/#website',
          'url': 'https://www.dentixs.app',
          'name': 'Dentix',
        },
        'breadcrumb': {
          '@type': 'BreadcrumbList',
          'itemListElement': [
            {
              '@type': 'ListItem',
              'position': 1,
              'name': homeBreadcrumb,
              'item': `https://www.dentixs.app${homeUrl}`,
            },
            {
              '@type': 'ListItem',
              'position': 2,
              'name': breadcrumbName,
              'item': canonicalUrl,
            },
          ],
        },
      },
    ],
  };

  return `<!DOCTYPE html>
<html lang="${lang}" dir="${dir}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(pageTitle)}</title>
  <meta name="description" content="${escapeHtml(metaDescription)}">
  <link rel="canonical" href="${canonicalUrl}">
  <link rel="alternate" hreflang="ar" href="${hreflangAr}">
  <link rel="alternate" hreflang="en" href="${hreflangEn}">
  <link rel="alternate" hreflang="x-default" href="${hreflangDefault}">
  <meta property="og:title" content="${escapeHtml(pageTitle)}">
  <meta property="og:description" content="${escapeHtml(metaDescription)}">
  <meta property="og:url" content="${canonicalUrl}">
  <meta property="og:site_name" content="Dentix">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="${isAr ? 'ar_EG' : 'en_US'}">
  <meta property="og:image" content="https://www.dentixs.app/logo.webp">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="${escapeHtml(pageTitle)}">
  <meta name="twitter:description" content="${escapeHtml(metaDescription)}">
  <meta name="twitter:image" content="https://www.dentixs.app/logo.webp">
  <link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon-180.png">
  ${isAr ? '<link rel="preload" href="/marketing/fonts/cairo-arabic.woff2" as="font" type="font/woff2" crossorigin>' : ''}
  <link rel="stylesheet" href="/marketing/marketing.css">
  <script type="application/ld+json">
${JSON.stringify(structuredData, null, 2)}
  </script>
</head>
<body>
  <a class="skip-link" href="#main">${isAr ? 'انتقل للمحتوى' : 'Skip to content'}</a>

  <header class="site-header">
    <div class="container">
      <nav class="navbar" aria-label="${isAr ? 'التنقل الرئيسي' : 'Main navigation'}">
        <a class="brand-wrapper" href="${homeUrl}" aria-label="Dentix">
          <img class="site-logo" src="/logo.webp" width="550" height="231" alt="Dentix — Smart Dental System">
        </a>
        <ul class="nav-links">
          <li><a href="${homeUrl}">${isAr ? 'الرئيسية' : 'Home'}</a></li>
          <li><a href="${termsUrl}">${isAr ? 'الشروط والأحكام' : 'Terms of Service'}</a></li>
          <li><a href="${privacyUrl}">${isAr ? 'سياسة الخصوصية' : 'Privacy Policy'}</a></li>
        </ul>
        <div class="nav-actions">
          <a class="btn-lang" href="${targetLangUrl}" hreflang="${targetLangCode}" aria-label="${targetLangAria}">${targetLangText}</a>
          <a class="nav-login" href="/">${isAr ? 'تسجيل الدخول' : 'Log in'}</a>
          <a class="btn btn-primary" href="/register">${isAr ? 'إنشاء حساب عيادة' : 'Create Clinic Account'}</a>
        </div>
      </nav>
    </div>
  </header>

  <main id="main" class="legal-main">
    <div class="container legal-container">
      <nav class="breadcrumbs" aria-label="${isAr ? 'مسار التنقل' : 'Breadcrumbs'}">
        <a href="${homeUrl}">${homeBreadcrumb}</a>
        <span aria-hidden="true">&rsaquo;</span>
        <span aria-current="page">${breadcrumbName}</span>
      </nav>

      <header class="legal-header">
        <h1 class="legal-title">${escapeHtml(data.title)}</h1>
        <p class="legal-meta">${escapeHtml(data.last_updated)}</p>
        <p class="legal-intro">${escapeHtml(data.intro)}</p>
      </header>

      <article class="legal-article">
${bodyContent}      </article>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-top">
        <a class="brand-wrapper" href="${homeUrl}" aria-label="Dentix">
          <img class="site-logo" src="/logo.webp" width="550" height="231" alt="Dentix — Smart Dental System">
        </a>
        <nav aria-label="${isAr ? 'روابط التذييل' : 'Footer navigation'}">
          <a href="${homeUrl}">${isAr ? 'الرئيسية' : 'Home'}</a>
          <a href="${termsUrl}">${isAr ? 'الشروط والأحكام' : 'Terms'}</a>
          <a href="${privacyUrl}">${isAr ? 'سياسة الخصوصية' : 'Privacy'}</a>
          <a href="/">${isAr ? 'تسجيل الدخول' : 'Log in'}</a>
          <a href="/register">${isAr ? 'تسجيل عيادة جديدة' : 'Create Clinic'}</a>
        </nav>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2026 Dentix. ${isAr ? 'جميع الحقوق محفوظة.' : 'All rights reserved.'}</p>
      </div>
    </div>
  </footer>
</body>
</html>
`;
}

export function generateAllLegalPages(outputBaseDir = null) {
  const { ar, en } = loadLocales();
  const baseDir = outputBaseDir || path.join(frontendRoot, 'public');

  const pages = [
    // 1. Arabic Privacy
    {
      filePath: path.join(baseDir, 'ar/privacy/index.html'),
      lang: 'ar',
      dir: 'rtl',
      pageType: 'privacy',
      data: ar.static.privacy,
      pageTitle: 'Dentix — سياسة الخصوصية',
      metaDescription: ar.static.privacy.intro.slice(0, 160),
      canonicalUrl: 'https://www.dentixs.app/ar/privacy',
      hreflangAr: 'https://www.dentixs.app/ar/privacy',
      hreflangEn: 'https://www.dentixs.app/en/privacy',
      hreflangDefault: 'https://www.dentixs.app/ar/privacy',
      targetLangUrl: '/en/privacy',
      targetLangText: 'English',
      targetLangAria: 'Switch to English Privacy Policy',
      targetLangCode: 'en',
    },
    // 2. English Privacy
    {
      filePath: path.join(baseDir, 'en/privacy/index.html'),
      lang: 'en',
      dir: 'ltr',
      pageType: 'privacy',
      data: en.static.privacy,
      pageTitle: 'Dentix — Privacy Policy',
      metaDescription: en.static.privacy.intro.slice(0, 160),
      canonicalUrl: 'https://www.dentixs.app/en/privacy',
      hreflangAr: 'https://www.dentixs.app/ar/privacy',
      hreflangEn: 'https://www.dentixs.app/en/privacy',
      hreflangDefault: 'https://www.dentixs.app/ar/privacy',
      targetLangUrl: '/ar/privacy',
      targetLangText: 'العربية',
      targetLangAria: 'التبديل إلى سياسة الخصوصية باللغة العربية',
      targetLangCode: 'ar',
    },
    // 3. Arabic Terms
    {
      filePath: path.join(baseDir, 'ar/terms/index.html'),
      lang: 'ar',
      dir: 'rtl',
      pageType: 'terms',
      data: ar.static.terms,
      pageTitle: 'Dentix — الشروط والأحكام',
      metaDescription: ar.static.terms.intro.slice(0, 160),
      canonicalUrl: 'https://www.dentixs.app/ar/terms',
      hreflangAr: 'https://www.dentixs.app/ar/terms',
      hreflangEn: 'https://www.dentixs.app/en/terms',
      hreflangDefault: 'https://www.dentixs.app/ar/terms',
      targetLangUrl: '/en/terms',
      targetLangText: 'English',
      targetLangAria: 'Switch to English Terms of Service',
      targetLangCode: 'en',
    },
    // 4. English Terms
    {
      filePath: path.join(baseDir, 'en/terms/index.html'),
      lang: 'en',
      dir: 'ltr',
      pageType: 'terms',
      data: en.static.terms,
      pageTitle: 'Dentix — Terms of Service',
      metaDescription: en.static.terms.intro.slice(0, 160),
      canonicalUrl: 'https://www.dentixs.app/en/terms',
      hreflangAr: 'https://www.dentixs.app/ar/terms',
      hreflangEn: 'https://www.dentixs.app/en/terms',
      hreflangDefault: 'https://www.dentixs.app/ar/terms',
      targetLangUrl: '/ar/terms',
      targetLangText: 'العربية',
      targetLangAria: 'التبديل إلى الشروط والأحكام باللغة العربية',
      targetLangCode: 'ar',
    },
  ];

  for (const page of pages) {
    const dirName = path.dirname(page.filePath);
    mkdirSync(dirName, { recursive: true });
    const html = generateLegalHtml(page);
    writeFileSync(page.filePath, html, 'utf8');
    console.log(`[generate-legal-pages] Wrote ${path.relative(frontendRoot, page.filePath)}`);
  }
}

// Run directly if CLI
const isCli = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isCli) {
  generateAllLegalPages(process.argv[2]);
}
