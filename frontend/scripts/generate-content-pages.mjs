#!/usr/bin/env node
/**
 * generate-content-pages.mjs
 * Generates static HTML pages for Trust & Content expansion in both Arabic and English:
 * - About Dentix (/ar/about, /en/about)
 * - Contact & Support (/ar/contact, /en/contact)
 * - Plans & Pricing (/ar/plans, /en/plans)
 * - Dental Clinic Management Software Guide (/ar/dental-clinic-management-software, /en/dental-clinic-management-software)
 * - Dental Patient Records Guide (/ar/dental-patient-records, /en/dental-patient-records)
 * - Dental Appointments & Finance Guide (/ar/appointments-finance, /en/appointments-finance)
 *
 * Guarantees:
 * - Zero executable JavaScript.
 * - Accurate product features matching verified capabilities.
 * - Approved contact details: smartsentalclinicapp@gmail.com & WhatsApp +201010285288.
 * - Approved plan names and prices (Essential 200 EGP, Professional 400 EGP, Business 1000 EGP).
 * - Omission of unverified limits and trial claims.
 * - Complete reciprocal hreflang clusters across all 6 bilingual page pairs.
 * - Valid Schema.org JSON-LD (AboutPage, ContactPage, WebPage, Article).
 * - Responsive semantic layout using marketing.css.
 */

import { writeFileSync, mkdirSync } from 'node:fs';
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

function renderBaseLayout({
  lang,
  dir,
  canonicalUrl,
  hreflangAr,
  hreflangEn,
  hreflangDefault,
  targetLangUrl,
  targetLangText,
  targetLangAria,
  targetLangCode,
  title,
  metaDescription,
  structuredData,
  breadcrumbName,
  contentHtml,
}) {
  const isAr = lang === 'ar';
  const homeUrl = isAr ? '/ar' : '/en';
  const homeBreadcrumb = isAr ? 'الرئيسية' : 'Home';

  return `<!DOCTYPE html>
<html lang="${lang}" dir="${dir}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <meta name="description" content="${escapeHtml(metaDescription)}">
  <link rel="canonical" href="${canonicalUrl}">
  <link rel="alternate" hreflang="ar" href="${hreflangAr}">
  <link rel="alternate" hreflang="en" href="${hreflangEn}">
  <link rel="alternate" hreflang="x-default" href="${hreflangDefault}">
  <meta property="og:title" content="${escapeHtml(title)}">
  <meta property="og:description" content="${escapeHtml(metaDescription)}">
  <meta property="og:url" content="${canonicalUrl}">
  <meta property="og:site_name" content="Dentix">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="${isAr ? 'ar_EG' : 'en_US'}">
  <meta property="og:image" content="https://www.dentixs.app/logo.webp">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="${escapeHtml(title)}">
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
          <li><a href="${isAr ? '/ar/about' : '/en/about'}">${isAr ? 'عن Dentix' : 'About'}</a></li>
          <li><a href="${isAr ? '/ar/plans' : '/en/plans'}">${isAr ? 'الباقات والأسعار' : 'Plans'}</a></li>
          <li><a href="${isAr ? '/ar/contact' : '/en/contact'}">${isAr ? 'تواصل معنا' : 'Contact'}</a></li>
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
        <span aria-current="page">${escapeHtml(breadcrumbName)}</span>
      </nav>

${contentHtml}
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
          <a href="${isAr ? '/ar/about' : '/en/about'}">${isAr ? 'عن Dentix' : 'About'}</a>
          <a href="${isAr ? '/ar/plans' : '/en/plans'}">${isAr ? 'الباقات' : 'Plans'}</a>
          <a href="${isAr ? '/ar/contact' : '/en/contact'}">${isAr ? 'تواصل معنا' : 'Contact'}</a>
          <a href="${isAr ? '/ar/dental-clinic-management-software' : '/en/dental-clinic-management-software'}">${isAr ? 'إدارة العيادات' : 'Clinic Guide'}</a>
          <a href="${isAr ? '/ar/dental-patient-records' : '/en/dental-patient-records'}">${isAr ? 'ملفات المرضى' : 'Patient Records'}</a>
          <a href="${isAr ? '/ar/appointments-finance' : '/en/appointments-finance'}">${isAr ? 'المواعيد والحسابات' : 'Appointments & Finance'}</a>
          <a href="${isAr ? '/ar/terms' : '/en/terms'}">${isAr ? 'الشروط والأحكام' : 'Terms'}</a>
          <a href="${isAr ? '/ar/privacy' : '/en/privacy'}">${isAr ? 'سياسة الخصوصية' : 'Privacy'}</a>
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

// 1. ABOUT PAGES
function getAboutAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">عن Dentix — برنامج إدارة عيادات الأسنان</h1>
        <p class="legal-meta">نظام سحابي متكامل مصمم خصيصاً لتنظيم العمل اليومي في عيادات ومراكز طب الأسنان.</p>
        <p class="legal-intro">يهدف Dentix إلى تحويل الإدارة التقليدية للعيادات إلى تجربة رقمية منظمة تجمع بين الملفات الطبية للمرضى، جدول المواعيد، مخطط الأسنان السريري، والحسابات المالية للعيادة في منصة واحدة تعمل عبر المتصفح.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>ما هو برنامج Dentix؟</h2>
          <p>Dentix هو نظام سحابي لإدارة عيادات طب الأسنان، صُمم لمساعدة أطباء الأسنان وفرق عملهم على إدارة العيادة بكفاءة وسلاسة. يتيح النظام الوصول الآمن للبيانات السريرية والإدارية من أجهزة الكمبيوتر والأجهزة اللوحية دون الحاجة إلى تثبيت خوادم محلية معقدة.</p>
        </section>

        <section class="prose-section">
          <h2>من يستفيد من نظام Dentix؟</h2>
          <ul class="prose-list">
            <li><strong>أطباء الأسنان والعيادات الفردية:</strong> لتوثيق الحالات السريرية، ومتابعة جلسات العلاج، والاطلاع الفوري على السجل الطبي لكل مريض.</li>
            <li><strong>المراكز والمجمعات السنية:</strong> لتنظيم المواعيد، وتوزيع المهام بين موظفي الاستقبال والأطباء، ومتابعة الإيرادات والمصروفات.</li>
            <li><strong>موظفو الاستقبال والإدارة:</strong> لإدارة قائمة الانتظار، وتسجيل المرضى الجدد، وتحصيل المدفوعات وإصدار الفواتير.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>لماذا إدارة عيادة الأسنان إلكترونياً مع Dentix؟</h2>
          <p>تواجه عيادات الأسنان تحديات مستمرة عند الاعتماد على السجلات الورقية، مثل ضياع ملفات المرضى، وتضارب المواعيد، وصعوبة تتبع المبالغ المتبقية على المرضى وتكاليف معامل الأسنان. يحل Dentix هذه العقبات عبر:</p>
          <ul class="prose-list">
            <li><strong>ملف إلكتروني موحد لكل مريض:</strong> يشمل البيانات الشخصية، التاريخ الطبي، التحذيرات المرضية، وسجل الزيارات السابقة.</li>
            <li><strong>مخطط الأسنان السريري (Odontogram):</strong> تدوين التشخيص والإجراءات العلاجية بدقة لكل سن وسطح.</li>
            <li><strong>جدول مواعيد مرن:</strong> رؤية واضحة لحالات الحجز (مؤكد، وصل العيادة، داخل غرفة الكشف، مكتمل).</li>
            <li><strong>انضباط مالي شامل:</strong> متابعة أسعار الخدمات، المبالغ المستلمة، الخصومات، والأرصدة المستحقة.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>واجهة ثنائية اللغة وتوافق عالي</h2>
          <p>يدعم نظام Dentix اللغتين العربية والإنجليزية بشكل أصيل مع اتجاه قراءة كامل (RTL/LTR). يستطيع كل مستخدم في العيادة اختيار اللغة المفضلة لديه بشكل مستقل، مما يسهل العمل على مختلف أعضاء الفريق الطبي والإداري.</p>
        </section>

        <section class="prose-section">
          <h2>دورة العمل داخل العيادة باستخدام Dentix</h2>
          <p>تم تصميم دورة العمل في النظام لتطابق الروتين الفعلي للعيادة السنية:</p>
          <ol class="prose-list" style="padding-inline-start: 24px; margin: 12px 0;">
            <li style="margin-bottom: 8px;"><strong>الاستقبال وتسجيل الوصول:</strong> تسجيل بيانات المريض الجديد أو استدعاء ملفه، وتأكيد موعد الزيارة ونقله إلى قائمة الانتظار.</li>
            <li style="margin-bottom: 8px;"><strong>الفحص السريري:</strong> يفتح الطبيب مخطط الأسنان، ويسجل الملاحظات والإجراءات المقترحة في خطة العلاج.</li>
            <li style="margin-bottom: 8px;"><strong>جلسة العلاج:</strong> توثيق خطوات الجلسة العلاجية، قياسات القنوات (في علاج الجذور)، والمواد المستخدمة.</li>
            <li style="margin-bottom: 8px;"><strong>المحاسبة والمغادرة:</strong> تحصيل الرسوم المقررة، وتحديث رصيد المريض، وحجز موعد الجلسة القادمة.</li>
          </ol>
        </section>

        <section class="prose-section">
          <h2>كيف تبدأ استخدام Dentix؟</h2>
          <p>يمكنك البدء فوراً بإنشاء حساب عيادتك عبر <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">صفحة إنشاء حساب عيادة</a>، أو تسجيل الدخول من <a href="/" style="color: var(--color-primary-dark); font-weight: 700;">بوابة الدخول</a>. كما يمكنك الاطلاع على <a href="/ar/plans" style="color: var(--color-primary-dark); font-weight: 700;">الباقات والأسعار المعتمدة</a> والتواصل مع فريق الدعم عبر <a href="/ar/contact" style="color: var(--color-primary-dark); font-weight: 700;">صفحة الاتصال والدعم</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/about',
    hreflangAr: 'https://www.dentixs.app/ar/about',
    hreflangEn: 'https://www.dentixs.app/en/about',
    hreflangDefault: 'https://www.dentixs.app/ar/about',
    targetLangUrl: '/en/about',
    targetLangText: 'English',
    targetLangAria: 'Switch to English About page',
    targetLangCode: 'en',
    title: 'Dentix — عن البرنامج ومميزات إدارة عيادات الأسنان',
    metaDescription: 'تعرف على برنامج Dentix لإدارة عيادات الأسنان: ملفات المرضى، مخطط الأسنان السريري، المواعيد، وتقارير الحسابات في نظام سحابي ثنائي اللغة.',
    structuredData: {
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
          '@type': 'AboutPage',
          '@id': 'https://www.dentixs.app/ar/about#webpage',
          'url': 'https://www.dentixs.app/ar/about',
          'name': 'Dentix — عن البرنامج ومميزات إدارة عيادات الأسنان',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'عن Dentix',
    contentHtml,
  });
}

function getAboutEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">About Dentix — Dental Clinic Management Software</h1>
        <p class="legal-meta">Comprehensive cloud platform designed specifically for dental practitioners, clinics, and multi-provider centers.</p>
        <p class="legal-intro">Dentix streamlines daily dental practice operations by bringing digital patient health records, interactive dental charting, appointment scheduling, and clinic financial management into one cohesive web platform.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>What is Dentix?</h2>
          <p>Dentix is modern cloud-based dental practice management software created to help dentists and clinic staff manage administrative and clinical workflows seamlessly. The platform enables secure access from desktop computers and tablets without requiring on-premise local servers or complicated IT hardware.</p>
        </section>

        <section class="prose-section">
          <h2>Who is Dentix For?</h2>
          <ul class="prose-list">
            <li><strong>Solo Dental Practices:</strong> To maintain digital patient records, monitor clinical treatments, and access treatment history at the operatory chair.</li>
            <li><strong>Dental Centers & Polyclinics:</strong> To organize appointment flows, coordinate receptionists with doctors, and manage operational clinic finances.</li>
            <li><strong>Receptionists & Practice Managers:</strong> To track the waiting room queue, schedule recall visits, collect payments, and issue clear treatment invoices.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Why Choose Cloud Dental Management with Dentix?</h2>
          <p>Traditional dental practices frequently encounter lost paper folders, double-booked appointments, uncollected patient balances, and untracked dental laboratory costs. Dentix solves these bottlenecks through:</p>
          <ul class="prose-list">
            <li><strong>Unified Digital Patient Records:</strong> Personal information, comprehensive medical alerts, past visit notes, and attached documents in one place.</li>
            <li><strong>Interactive Clinical Dental Chart (Odontogram):</strong> Visual tooth-by-tooth diagnosis and surface-level procedure documentation.</li>
            <li><strong>Flexible Appointment Management:</strong> Real-time status progression from scheduled to arrived, in-chair, and completed.</li>
            <li><strong>Financial Clarity:</strong> Transparent billing per procedure, payment receipts, discounts, remaining patient balances, and clinic expense logging.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Bilingual Architecture (Arabic & English)</h2>
          <p>Dentix natively supports both Arabic and English with full bidirectional typography (RTL/LTR). Each staff member can configure their preferred interface language independently, fostering effective collaboration across clinical and administrative personnel.</p>
        </section>

        <section class="prose-section">
          <h2>Typical Daily Practice Workflow</h2>
          <ol class="prose-list" style="padding-inline-start: 24px; margin: 12px 0;">
            <li style="margin-bottom: 8px;"><strong>Check-in & Reception:</strong> Register new patients or retrieve existing files, confirm appointments, and move patients to the waiting queue.</li>
            <li style="margin-bottom: 8px;"><strong>Clinical Examination:</strong> The dentist reviews the dental chart, examines surfaces, and establishes a treatment plan.</li>
            <li style="margin-bottom: 8px;"><strong>Care Session Documentation:</strong> Record procedure progress, endodontic canal measurements, materials, and clinical observations.</li>
            <li style="margin-bottom: 8px;"><strong>Billing & Recall:</strong> Settle payment receipts, update outstanding ledger balances, and schedule the next follow-up visit.</li>
          </ol>
        </section>

        <section class="prose-section">
          <h2>Getting Started with Dentix</h2>
          <p>You can begin today by opening your clinic account via the <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">Clinic Registration page</a>, or access your existing portal through <a href="/" style="color: var(--color-primary-dark); font-weight: 700;">Login</a>. Explore our <a href="/en/plans" style="color: var(--color-primary-dark); font-weight: 700;">Approved Subscription Plans</a> and get in touch with our team via the <a href="/en/contact" style="color: var(--color-primary-dark); font-weight: 700;">Contact & Support page</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/about',
    hreflangAr: 'https://www.dentixs.app/ar/about',
    hreflangEn: 'https://www.dentixs.app/en/about',
    hreflangDefault: 'https://www.dentixs.app/ar/about',
    targetLangUrl: '/ar/about',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى صفحة عن Dentix باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — About Dentix Dental Clinic Management Software',
    metaDescription: 'Learn about Dentix: cloud dental practice management software for patient records, interactive dental charting, appointment scheduling, and clinic finances.',
    structuredData: {
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
          '@type': 'AboutPage',
          '@id': 'https://www.dentixs.app/en/about#webpage',
          'url': 'https://www.dentixs.app/en/about',
          'name': 'Dentix — About Dentix Dental Clinic Management Software',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'About Dentix',
    contentHtml,
  });
}

// 2. CONTACT PAGES
function getContactAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">تواصل مع فريق Dentix</h1>
        <p class="legal-meta">يسعدنا الإجابة عن استفساراتكم وتقديم الدعم الفني لعيادتكم عبر القنوات الرسمية المعتمدة.</p>
        <p class="legal-intro">فريق الدعم الفني والمبيعات في Dentix متاح لمساعدتكم في تفعيل حسابات العيادات، إعداد خطط الاشتراك، وحل أية استفسارات تقنية متعلقة بالنظام.</p>
      </header>

      <div class="contact-grid">
        <div class="contact-card">
          <div class="contact-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
          </div>
          <h3>البريد الإلكتروني للدعم</h3>
          <p>أرسل لنا استفساراتك التقنية أو متطلبات عيادتك وسنقوم بالرد عليك مباشرة.</p>
          <a class="btn btn-secondary" href="mailto:smartsentalclinicapp@gmail.com">smartsentalclinicapp@gmail.com</a>
        </div>

        <div class="contact-card">
          <div class="contact-icon" aria-hidden="true" style="color: #16a34a; background: #dcfce7;">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          </div>
          <h3>المحادثة الفورية عبر واتساب</h3>
          <p>تواصل مع فريق الدعم والمبيعات مباشرة عبر تطبيق واتساب لسرعة الرد والمساعدة الفورية.</p>
          <a class="btn btn-primary" href="https://wa.me/201010285288" target="_blank" rel="noopener">+201010285288</a>
        </div>
      </div>

      <article class="legal-article">
        <section class="prose-section">
          <h2>قنوات التواصل الرسمية لعيادات الأسنان</h2>
          <p>لضمان سرعة الخدمة، يرجى استخدام القناتين الرسميتين المعتمدتين أعلاه (البريد الإلكتروني ورقم الواتساب الرسمي). يتم التعامل مع استفسارات التسجيل، تجديد الاشتراكات، وملاحظات الاستخدام التقنية مباشرة عبر هاتين القناتين.</p>
        </section>

        <section class="prose-section">
          <h2>الدعم الفني وتفعيل الاشتراكات</h2>
          <p>وفقاً لسياسة النظام المعتمدة، يتم تفعيل وتجديد اشتراكات العيادات من خلال التواصل المباشر مع فريق الدعم الفني. إذا كانت لديك عيادة مسجلة وترغب في ترقية باقتك، يمكنك مراسلتنا مباشرة عبر الواتساب مع ذكر اسم العيادة لتأكيد التفعيل.</p>
          <div class="prose-alert">
            نحرص على أمان وسرية بيانات عيادتكم. لا نطلب أبداً كلمات المرور الخاصة بحساباتكم السريرية عند التواصل مع الدعم.
          </div>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/contact',
    hreflangAr: 'https://www.dentixs.app/ar/contact',
    hreflangEn: 'https://www.dentixs.app/en/contact',
    hreflangDefault: 'https://www.dentixs.app/ar/contact',
    targetLangUrl: '/en/contact',
    targetLangText: 'English',
    targetLangAria: 'Switch to English Contact page',
    targetLangCode: 'en',
    title: 'Dentix — تواصل مع فريق الدعم والمبيعات',
    metaDescription: 'تواصل مع فريق Dentix لإدارة عيادات الأسنان عبر البريد الإلكتروني smartsentalclinicapp@gmail.com أو الواتساب الرسمي +201010285288.',
    structuredData: {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': 'Organization',
          '@id': 'https://www.dentixs.app/#organization',
          'name': 'Dentix',
          'url': 'https://www.dentixs.app',
          'logo': 'https://www.dentixs.app/logo.webp',
          'contactPoint': {
            '@type': 'ContactPoint',
            'contactType': 'customer support',
            'email': 'smartsentalclinicapp@gmail.com',
            'telephone': '+201010285288',
            'availableLanguage': ['Arabic', 'English'],
          },
        },
        {
          '@type': 'ContactPage',
          '@id': 'https://www.dentixs.app/ar/contact#webpage',
          'url': 'https://www.dentixs.app/ar/contact',
          'name': 'Dentix — تواصل مع فريق الدعم والمبيعات',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'تواصل معنا',
    contentHtml,
  });
}

function getContactEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">Contact Dentix Support & Sales</h1>
        <p class="legal-meta">We are here to answer your questions and provide technical assistance for your dental practice.</p>
        <p class="legal-intro">The Dentix team is available through our official channels to support clinic onboarding, assist with plan activations, and answer technical product questions.</p>
      </header>

      <div class="contact-grid">
        <div class="contact-card">
          <div class="contact-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
          </div>
          <h3>Support Email</h3>
          <p>Send us your technical inquiries or practice requirements for direct assistance.</p>
          <a class="btn btn-secondary" href="mailto:smartsentalclinicapp@gmail.com">smartsentalclinicapp@gmail.com</a>
        </div>

        <div class="contact-card">
          <div class="contact-icon" aria-hidden="true" style="color: #16a34a; background: #dcfce7;">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          </div>
          <h3>Official WhatsApp Chat</h3>
          <p>Chat directly with our support team on WhatsApp for prompt guidance and onboarding support.</p>
          <a class="btn btn-primary" href="https://wa.me/201010285288" target="_blank" rel="noopener">+201010285288</a>
        </div>
      </div>

      <article class="legal-article">
        <section class="prose-section">
          <h2>Official Channels for Dental Clinics</h2>
          <p>To ensure prompt and secure handling of your requests, please use the approved official channels above (official support email and WhatsApp number). All clinic onboarding requests, plan renewals, and technical inquiries are handled directly through these verified points of contact.</p>
        </section>

        <section class="prose-section">
          <h2>Subscription Activation & Assistance</h2>
          <p>Under our approved practice policy, clinic subscriptions and renewals are arranged directly through system administration and support. If you have registered a clinic and wish to activate or adjust your tier, message our team with your clinic name for confirmation.</p>
          <div class="prose-alert">
            We prioritize data confidentiality and clinical security. Dentix representatives will never ask for your private account passwords.
          </div>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/contact',
    hreflangAr: 'https://www.dentixs.app/ar/contact',
    hreflangEn: 'https://www.dentixs.app/en/contact',
    hreflangDefault: 'https://www.dentixs.app/ar/contact',
    targetLangUrl: '/ar/contact',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى صفحة التواصل باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — Contact Support & Sales',
    metaDescription: 'Contact Dentix dental clinic management software via support email smartsentalclinicapp@gmail.com or official WhatsApp at +201010285288.',
    structuredData: {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': 'Organization',
          '@id': 'https://www.dentixs.app/#organization',
          'name': 'Dentix',
          'url': 'https://www.dentixs.app',
          'logo': 'https://www.dentixs.app/logo.webp',
          'contactPoint': {
            '@type': 'ContactPoint',
            'contactType': 'customer support',
            'email': 'smartsentalclinicapp@gmail.com',
            'telephone': '+201010285288',
            'availableLanguage': ['Arabic', 'English'],
          },
        },
        {
          '@type': 'ContactPage',
          '@id': 'https://www.dentixs.app/en/contact#webpage',
          'url': 'https://www.dentixs.app/en/contact',
          'name': 'Dentix — Contact Support & Sales',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'Contact & Support',
    contentHtml,
  });
}

// 3. PLANS PAGES
function getPlansAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">باقات وأسعار اشتراك Dentix</h1>
        <p class="legal-meta">خطط شهرية واضحة ومناسبة لمختلف أحجام العيادات والمراكز السنية.</p>
        <p class="legal-intro">اختر الباقة المناسبة لاحتياجات عيادتك الطبية والإدارية. تشتمل كافة الباقات على بيئة سحابية آمنة، دعم كامل للغة العربية والإنجليزية، وإمكانية الوصول من أجهزة متعددة.</p>
      </header>

      <div class="plans-grid">
        <!-- 1. Essential Plan -->
        <div class="plan-card">
          <div class="plan-name">الأساسية (Essential)</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">للعيادات الفردية الراغبة في تنظيم المواعيد وسجلات المرضى رقمياً.</p>
          <div class="plan-price">200 <span>ج.م</span></div>
          <div class="plan-period">شهرياً</div>
          <ul class="plan-features">
            <li>سجل إلكتروني متكامل لملفات المرضى</li>
            <li>جدول مواعيد تفاعلي وتنظيم قائمة الانتظار</li>
            <li>إصدار فواتير وسندات القبض الأساسية</li>
            <li>واجهة ثنائية اللغة (عربي / إنجليزي)</li>
            <li>حفظ سحابي آمن وتحديثات النظام الدورية</li>
          </ul>
          <a class="btn btn-secondary" href="https://wa.me/201010285288?text=%D8%A3%D8%B1%D8%BA%D8%A8%20%D9%81%D9%8A%20%D8%A7%D9%84%D8%A7%D8%B4%D8%AA%D8%B1%D8%A7%D9%83%20%D9%81%D9%8A%20%D8%A8%D8%A7%D9%82%D8%A9%20%D8%A7%D9%84%D8%A3%D8%B3%D8%A7%D8%B3%D9%8A%D8%A9" target="_blank" rel="noopener">طلب الباقة الأساسية</a>
        </div>

        <!-- 2. Professional Plan -->
        <div class="plan-card featured">
          <span class="plan-badge">الأكثر طلباً</span>
          <div class="plan-name">الاحترافية (Professional)</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">للعيادات النشطة التي تتطلب توثيقاً سريرياً دقيقاً ومتابعة مالية كاملة.</p>
          <div class="plan-price">400 <span>ج.م</span></div>
          <div class="plan-period">شهرياً</div>
          <ul class="plan-features">
            <li>كافة مميزات الباقة الأساسية</li>
            <li>مخطط الأسنان السريري التفاعلي (Odontogram)</li>
            <li>سجلات علاج الجذور وقياسات القنوات التفصيلية</li>
            <li>متابعة ديون وحسابات معامل الأسنان</li>
            <li>تقارير إيرادات ومصروفات مالية تفصيلية</li>
            <li>دعم فني مباشر وسريع</li>
          </ul>
          <a class="btn btn-primary" href="https://wa.me/201010285288?text=%D8%A3%D8%B1%D8%BA%D8%A8%20%D9%81%D9%8A%20%D8%A7%D9%84%D8%A7%D8%B4%D8%AA%D8%B1%D8%A7%D9%83%20%D9%81%D9%8A%20%D8%A7%D9%84%D8%A8%D8%A7%D9%82%D8%A9%20%D8%A7%D9%84%D8%A7%D8%AD%D8%AA%D8%B1%D8%A7%D9%81%D9%8A%D8%A9" target="_blank" rel="noopener">طلب الباقة الاحترافية</a>
        </div>

        <!-- 3. Business Plan -->
        <div class="plan-card">
          <div class="plan-name">الأعمال (Business)</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">للمراكز السنية والمجمعات الطبية ذات الإشغال العالي والفرق المتعددة.</p>
          <div class="plan-price">1000 <span>ج.م</span></div>
          <div class="plan-period">شهرياً</div>
          <ul class="plan-features">
            <li>كافة مميزات الباقة الاحترافية</li>
            <li>إدارة شاملة لعيادات وفروع متعددة</li>
            <li>متابعة حركة المخزون والمواد المستهلكة في العيادة</li>
            <li>تحليلات أداء ومؤشرات مالية وسريرية موسعة</li>
            <li>أولوية قصوى في الدعم الفني والتأهيل الميداني</li>
          </ul>
          <a class="btn btn-secondary" href="https://wa.me/201010285288?text=%D8%A3%D8%B1%D8%BA%D8%A8%20%D9%81%D9%8A%20%D8%A7%D9%84%D8%A7%D8%B4%D8%AA%D8%B1%D8%A7%D9%83%20%D9%81%D9%8A%20%D8%A8%D8%A7%D9%82%D8%A9%20%D8%A7%D9%84%D8%A3%D8%B9%D9%85%D8%A7%D9%84" target="_blank" rel="noopener">طلب باقة الأعمال</a>
        </div>
      </div>

      <article class="legal-article">
        <section class="prose-section">
          <h2>كيف يتم تفعيل الاشتراك؟</h2>
          <p>حرصاً على مرونة الخدمة والتأكد من مطابقة النظام لمتطلبات كل عيادة، يتم تفعيل الاشتراكات وتجديدها حصرياً عبر التواصل المباشر مع إدارة المنظومة وفريق الدعم الفني عبر الواتساب أو البريد الإلكتروني.</p>
          <div class="prose-alert">
            <strong>سياسة البيانات الطبية:</strong> تبقى سجلات المرضى والملفات السريرية لعيادتكم متاحة دائماً للاطلاع والقراءة حتى في حال انتهاء فترة الاشتراك، حفاظاً على استمرارية الرعاية الطبية للمرضى.
          </div>
        </section>

        <section class="prose-section">
          <h2>طريقة الدفع والتجديد</h2>
          <p>تتم تسوية الاشتراكات الشهرية بالجنيه المصري (EGP) عبر وسائل التحويل والمدفوعات المتفق عليها مع الدعم الفني. لتفعيل باقتك، يمكنك الضغط على زر الطلب المباشر لأي باقة أو مراسلتنا على <a href="https://wa.me/201010285288" style="color: var(--color-primary-dark); font-weight: 700;">+201010285288</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/plans',
    hreflangAr: 'https://www.dentixs.app/ar/plans',
    hreflangEn: 'https://www.dentixs.app/en/plans',
    hreflangDefault: 'https://www.dentixs.app/ar/plans',
    targetLangUrl: '/en/plans',
    targetLangText: 'English',
    targetLangAria: 'Switch to English Plans & Pricing page',
    targetLangCode: 'en',
    title: 'Dentix — خطط وباقات إدارة عيادات الأسنان',
    metaDescription: 'تعرف على أسعار وباقات برنامج Dentix لإدارة عيادات الأسنان: الأساسية 200 ج.م، الاحترافية 400 ج.م، وباقة الأعمال 1000 ج.م شهرياً.',
    structuredData: {
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
          '@id': 'https://www.dentixs.app/ar/plans#webpage',
          'url': 'https://www.dentixs.app/ar/plans',
          'name': 'Dentix — خطط وباقات إدارة عيادات الأسنان',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'الباقات والأسعار',
    contentHtml,
  });
}

function getPlansEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">Dentix Plans & Pricing for Dental Clinics</h1>
        <p class="legal-meta">Straightforward monthly subscriptions designed for individual practices and growing dental centers.</p>
        <p class="legal-intro">Choose the subscription that fits your practice workflow. All plans provide secure cloud hosting, full bilingual Arabic and English support, and multi-device browser access.</p>
      </header>

      <div class="plans-grid">
        <!-- 1. Essential Plan -->
        <div class="plan-card">
          <div class="plan-name">Essential</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">For solo practitioners transitioning to digital records and appointment management.</p>
          <div class="plan-price">200 <span>EGP</span></div>
          <div class="plan-period">Per month</div>
          <ul class="plan-features">
            <li>Complete digital patient record management</li>
            <li>Interactive appointment book and waiting queue</li>
            <li>Basic billing, invoices, and payment receipts</li>
            <li>Bilingual Arabic and English interface</li>
            <li>Secure cloud storage and continuous system updates</li>
          </ul>
          <a class="btn btn-secondary" href="https://wa.me/201010285288?text=I%20am%20interested%20in%20the%20Essential%20Plan" target="_blank" rel="noopener">Select Essential Plan</a>
        </div>

        <!-- 2. Professional Plan -->
        <div class="plan-card featured">
          <span class="plan-badge">Most Popular</span>
          <div class="plan-name">Professional</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">For active clinics requiring detailed clinical dental charting and financial tracking.</p>
          <div class="plan-price">400 <span>EGP</span></div>
          <div class="plan-period">Per month</div>
          <ul class="plan-features">
            <li>All Essential Plan capabilities</li>
            <li>Interactive clinical dental chart (Odontogram)</li>
            <li>Detailed root canal session & canal measurement logging</li>
            <li>Dental lab order and technician balance tracking</li>
            <li>Comprehensive revenue and expense reports</li>
            <li>Direct technical support access</li>
          </ul>
          <a class="btn btn-primary" href="https://wa.me/201010285288?text=I%20am%20interested%20in%20the%20Professional%20Plan" target="_blank" rel="noopener">Select Professional Plan</a>
        </div>

        <!-- 3. Business Plan -->
        <div class="plan-card">
          <div class="plan-name">Business</div>
          <p style="font-size: 13px; color: var(--muted); margin: 0 0 12px;">For busy dental centers and multi-operatory practices managing larger teams.</p>
          <div class="plan-price">1000 <span>EGP</span></div>
          <div class="plan-period">Per month</div>
          <ul class="plan-features">
            <li>All Professional Plan capabilities</li>
            <li>Comprehensive multi-operatory practice management</li>
            <li>Clinic inventory and consumable material tracking</li>
            <li>Extended financial reports and clinical analytics</li>
            <li>Priority onboarding and technical customer service</li>
          </ul>
          <a class="btn btn-secondary" href="https://wa.me/201010285288?text=I%20am%20interested%20in%20the%20Business%20Plan" target="_blank" rel="noopener">Select Business Plan</a>
        </div>
      </div>

      <article class="legal-article">
        <section class="prose-section">
          <h2>How Subscription Activation Works</h2>
          <p>To ensure smooth onboarding tailored to each clinic's specific practice setup, subscriptions are coordinated directly with our system administration and support team via WhatsApp or official email.</p>
          <div class="prose-alert">
            <strong>Medical Data Guarantee:</strong> Your patient health records, clinical notes, and treatment histories remain permanently accessible in read-only mode even if your active subscription term expires, safeguarding continuous clinical patient care.
          </div>
        </section>

        <section class="prose-section">
          <h2>Billing and Inquiries</h2>
          <p>Plans are billed monthly in Egyptian Pounds (EGP). To activate your chosen plan or discuss your practice requirements, select any plan card button above or message our team directly via WhatsApp at <a href="https://wa.me/201010285288" style="color: var(--color-primary-dark); font-weight: 700;">+201010285288</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/plans',
    hreflangAr: 'https://www.dentixs.app/ar/plans',
    hreflangEn: 'https://www.dentixs.app/en/plans',
    hreflangDefault: 'https://www.dentixs.app/ar/plans',
    targetLangUrl: '/ar/plans',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى صفحة الباقات والأسعار باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — Plans & Pricing for Dental Clinics',
    metaDescription: 'Explore approved monthly pricing for Dentix dental clinic software: Essential 200 EGP, Professional 400 EGP, and Business 1000 EGP per month.',
    structuredData: {
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
          '@id': 'https://www.dentixs.app/en/plans#webpage',
          'url': 'https://www.dentixs.app/en/plans',
          'name': 'Dentix — Plans & Pricing for Dental Clinics',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'Plans & Pricing',
    contentHtml,
  });
}

// 4. CONTENT PAGE 1: DENTAL CLINIC MANAGEMENT SOFTWARE
function getClinicSoftwareAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">برنامج إدارة عيادات الأسنان: دليلك لتنظيم العمل السريري والإداري</h1>
        <p class="legal-meta">كيف يساعد التحول الرقمي في تنظيم ملفات المرضى، جدول المواعيد، الفحص السريري، وحسابات عيادة الأسنان.</p>
        <p class="legal-intro">تتطلب عيادة الأسنان الحديثة تنظيماً دقيقاً يربط بين موظف الاستقبال، المساعد، وطبيب الأسنان في غرفة الكشف. يقدم Dentix حلاً سحابياً شاملاً يُنهي فوضى السجلات الورقية ويوحد إدارة العيادة بالكامل.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>تحديات الإدارة الورقية في عيادة الأسنان</h2>
          <p>تعتمد العديد من عيادات الأسنان على الدفاتر الورقية أو ملفات Excel المتفرقة، مما يؤدي إلى عقبات يومية تؤثر على جودة الرعاية السريرية وربحية العيادة:</p>
          <ul class="prose-list">
            <li><strong>تلف أو ضياع السجلات السريرية:</strong> صعوبة العثور على تاريخ المريض عند حضوره المفاجئ، أو نسيان التحسسات الدوائية السابقة.</li>
            <li><strong>تضارب المواعيد والانتظار الطويل:</strong> حجز مواعيد متعددة في نفس الوقت أو عدم وضوح أولوية الدخول إلى غرفة الكشف.</li>
            <li><strong>صعوبة توثيق خطط العلاج:</strong> غياب مخطط مرئي للأسنان يبين حالة كل سن قبل وبعد العلاج.</li>
            <li><strong>تسرب الإيرادات وعدم انضباط الحسابات:</strong> تراكم الديون غير المحصلة وصعوبة مطابقة تكاليف المعامل والمواد المستهلكة.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>أركان برنامج إدارة العيادة السحابي الناجح</h2>
          <p>يقوم نظام Dentix على أربعة أركان أساسية تغطي كافة جوانب عمل العيادة:</p>
          <ol class="prose-list" style="padding-inline-start: 24px; margin: 12px 0;">
            <li style="margin-bottom: 12px;"><strong>إدارة المرضى والسجل الطبي:</strong> ملف إلكتروني متكامل يحتوي على التاريخ المرضي، التنبيهات الصحية (مثل السكري أو ضغط الدم)، وصور الأشعة والمرفقات السريرية.</li>
            <li style="margin-bottom: 12px;"><strong>جدول المواعيد وقائمة الانتظار:</strong> متابعة مواعيد اليوم لحظة بلحظة، وتحديث حالة المريض من وصوله وحتى خروجه.</li>
            <li style="margin-bottom: 12px;"><strong>مخطط الأسنان السريري وجلسات العلاج:</strong> تسجيل كل إجراء على السن وسطحه بدقة، مع توثيق تفاصيل حشوات الجذور والتركيبات.</li>
            <li style="margin-bottom: 12px;"><strong>الإدارة المالية الدقيقة:</strong> إصدار فواتير وسندات سداد فورية، وتتبع حسابات المعامل والمصروفات التشغيلية.</li>
          </ol>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/dashboard-ar.webp" width="1440" height="1000" alt="لوحة معلومات وإحصائيات عيادة الأسنان في Dentix" loading="lazy">
          <figcaption>لوحة معلومات Dentix — شاشة حقيقية توضح إحصائيات المواعيد، الإيرادات، وحركة العيادة اليومية (بيانات توضيحية افتراضية).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>خطوات التحول الرقمي في عيادتك</h2>
          <p>لا يتطلب التحول الرقمي مع Dentix سوى خطوات بسيطة ومباشرة:</p>
          <ul class="prose-list">
            <li><strong>الخطوة الأولى:</strong> إنشاء حساب عيادتك عبر <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">صفحة التسجيل</a>.</li>
            <li><strong>الخطوة الثانية:</strong> إعداد قائمة أسعار الخدمات والإجراءات السريرية المتبعة في عيادتك.</li>
            <li><strong>الخطوة الثالثة:</strong> إضافة موظفي العيادة وتحديد صلاحية كل مستخدم (طبيب، استقبال، إدارة).</li>
            <li><strong>الخطوة الرابعة:</strong> البدء في تسجيل المرضى والمواعيد مباشرة من أي متصفح إنترنت.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>ابدأ بتطوير إدارة عيادتك اليوم</h2>
          <p>اكتشف كيف يساعدك Dentix في تنظيم عيادتك عبر استعراض <a href="/ar/plans" style="color: var(--color-primary-dark); font-weight: 700;">الباقات والأسعار المعتمدة</a>، أو راجع <a href="/ar/dental-patient-records" style="color: var(--color-primary-dark); font-weight: 700;">دليل إدارة ملفات المرضى إلكترونياً</a> لمعرفة تفاصيل التوثيق السريري ومخطط الأسنان.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    hreflangAr: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    hreflangEn: 'https://www.dentixs.app/en/dental-clinic-management-software',
    hreflangDefault: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    targetLangUrl: '/en/dental-clinic-management-software',
    targetLangText: 'English',
    targetLangAria: 'Switch to English Dental Clinic Management Software guide',
    targetLangCode: 'en',
    title: 'Dentix — برنامج إدارة عيادات الأسنان: دليلك لتنظيم العمل السريري والإداري',
    metaDescription: 'دليل شامل حول برنامج إدارة عيادات الأسنان Dentix: تنظيم ملفات المرضى، جدول المواعيد، مخطط الأسنان السريري، وحسابات العيادة بدقة وكفاءة.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/ar/dental-clinic-management-software#webpage',
          'url': 'https://www.dentixs.app/ar/dental-clinic-management-software',
          'headline': 'برنامج إدارة عيادات الأسنان: دليلك لتنظيم العمل السريري والإداري',
          'description': 'دليل شامل حول برنامج إدارة عيادات الأسنان Dentix وكيفية تنظيم المواعيد والملفات والحسابات.',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'إدارة عيادات الأسنان',
    contentHtml,
  });
}

function getClinicSoftwareEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">Dental Clinic Management Software: Complete Practice Workflow Guide</h1>
        <p class="legal-meta">How cloud software streamlines patient files, appointment scheduling, clinical charting, and dental finances.</p>
        <p class="legal-intro">Modern dental practices require seamless coordination between the reception desk, dental assistants, and dentists at the chair. Dentix delivers a unified cloud solution that replaces fragmented paper systems and centralizes clinic operations.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>The Challenges of Paper-Based Dental Administration</h2>
          <p>Relying on physical paper charts or disconnected spreadsheets creates recurring friction that affects patient retention and practice profitability:</p>
          <ul class="prose-list">
            <li><strong>Misplaced Clinical Folders:</strong> Searching for paper charts when a patient arrives without notice, risking missed medical alerts.</li>
            <li><strong>Scheduling Conflicts & Waiting Room Chaos:</strong> Overlapping bookings, unknown patient arrival times, and delayed doctor handoffs.</li>
            <li><strong>Incomplete Treatment Documentation:</strong> Missing visual tooth charts that clearly delineate existing conditions from proposed procedures.</li>
            <li><strong>Uncollected Balances & Untracked Lab Expenses:</strong> Accumulated patient debts and difficult reconciliation with dental laboratories.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Core Pillars of Cloud Dental Management</h2>
          <p>Dentix structures practice workflows across four connected architectural components:</p>
          <ol class="prose-list" style="padding-inline-start: 24px; margin: 12px 0;">
            <li style="margin-bottom: 12px;"><strong>Digital Patient Health Records:</strong> Centralized histories, chronic medical flags, allergies, attachments, and visit timelines.</li>
            <li style="margin-bottom: 12px;"><strong>Appointment Scheduling & Queue:</strong> Real-time operatory schedules tracking booked, arrived, seated, and finished visits.</li>
            <li style="margin-bottom: 12px;"><strong>Clinical Dental Charting (Odontogram):</strong> Visual surface-level diagnostic notes and endodontic canal measurement documentation.</li>
            <li style="margin-bottom: 12px;"><strong>Practice Accounting & Ledger:</strong> Itemized procedure billing, partial payments, lab debt tracking, and operational overhead logging.</li>
          </ol>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/dashboard-en.webp" width="1440" height="1000" alt="Dentix dental clinic dashboard showing real operational statistics" loading="lazy">
          <figcaption>Dentix Dashboard — Real interface screen illustrating appointment queues, revenue statistics, and clinic performance (fictional demonstration data).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>Steps to Digital Practice Modernization</h2>
          <p>Adopting Dentix requires straightforward, non-disruptive steps:</p>
          <ul class="prose-list">
            <li><strong>Step 1:</strong> Create your clinic account on the <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">Registration page</a>.</li>
            <li><strong>Step 2:</strong> Configure your clinic service price list and procedure catalog.</li>
            <li><strong>Step 3:</strong> Add staff accounts with designated roles (Doctor, Reception, Admin).</li>
            <li><strong>Step 4:</strong> Manage patient check-ins and appointments from any web browser or tablet.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Start Managing Your Clinic With Clarity</h2>
          <p>Explore our approved plans on the <a href="/en/plans" style="color: var(--color-primary-dark); font-weight: 700;">Plans & Pricing page</a>, or discover our dedicated guide on <a href="/en/dental-patient-records" style="color: var(--color-primary-dark); font-weight: 700;">Digital Dental Patient Records</a> for in-depth charting details.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/dental-clinic-management-software',
    hreflangAr: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    hreflangEn: 'https://www.dentixs.app/en/dental-clinic-management-software',
    hreflangDefault: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    targetLangUrl: '/ar/dental-clinic-management-software',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى دليل برنامج إدارة عيادات الأسنان باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — Dental Clinic Management Software: Complete Practice Workflow Guide',
    metaDescription: 'Complete guide to dental clinic management software: organize patient charts, appointment queues, interactive odontograms, and practice billing with Dentix.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/en/dental-clinic-management-software#webpage',
          'url': 'https://www.dentixs.app/en/dental-clinic-management-software',
          'headline': 'Dental Clinic Management Software: Complete Practice Workflow Guide',
          'description': 'Comprehensive guide on cloud dental clinic management software, patient records, charting, and appointments.',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'Dental Clinic Management',
    contentHtml,
  });
}

// 5. CONTENT PAGE 2: DENTAL PATIENT RECORDS MANAGEMENT
function getPatientRecordsAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">إدارة ملفات مرضى الأسنان إلكترونيًا وسجلات العلاج</h1>
        <p class="legal-meta">دليل مفصل حول السجل الطبي الإلكتروني للمريض، مخطط الأسنان السريري، وتوثيق جلسات العلاج.</p>
        <p class="legal-intro">يمثل ملف المريض قلب العمل الإكلينيكي في عيادة الأسنان. يوفر Dentix ملفاً طبياً إلكترونياً شاملاً يجمع بين التاريخ الصحي للمريض، مخطط الأسنان التفاعلي (Odontogram)، وتوثيق كل جلسة علاجية بدقة متناهية.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>أهمية السجل الطبي الإلكتروني في طب الأسنان</h2>
          <p>يتطلب علاج الأسنان دقة متناهية وتتبعاً دقيقاً لتاريخ العلاجات السابقة لكل سن. يحقق الملف الإلكتروني في Dentix أعلى معايير الجودة السريرية من خلال:</p>
          <ul class="prose-list">
            <li><strong>التنبيهات الصحية والتاريخ الطبي:</strong> تسجيل الأمراض المزمنة (القلب، السكري، ضغط الدم) وأية حساسية تجاه الأدوية والمخدر الموضعي لتنبيه الطبيب فور فتح الملف.</li>
            <li><strong>توثيق تسلسل الزيارات:</strong> تدوين ملاحظات الطبيب في كل جلسة مع تسجيل التاريخ والوقت واسم الطبيب المعالج.</li>
            <li><strong>حفظ صور الأشعة والمرفقات:</strong> ربط الأشعة السينية (Periapical / Panoramic) بملف المريض للرجوع إليها في أي وقت.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>مخطط الأسنان السريري التفاعلي (Odontogram)</h2>
          <p>يقدم Dentix مخططاً بيانياً تفاعلياً لأسنان البالغين والأطفال، يتيح لطبيب الأسنان:</p>
          <ul class="prose-list">
            <li>فحص وتحديد حالة كل سن وأسطحه المختلفة (Mesial, Distal, Occlusal, Buccal, Lingual).</li>
            <li>تمييز الإجراءات السابقة (مثل الحشوات القائمة، التيجان، الأسنان المفقودة).</li>
            <li>إدراج خطط العلاج المستقبلية وتحديد أولوياتها وفق رغبة المريض والميزانية المحددة.</li>
            <li>متابعة جلسات علاج الجذور (Endodontics) وتوثيق قياسات أطوال القنوات وحجم المبارد ونسبة الاستدقاق (Taper).</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/chart-ar.webp" width="1440" height="1000" alt="مخطط الأسنان السريري التفاعلي في برنامج Dentix" loading="lazy">
          <figcaption>مخطط الأسنان السريري في Dentix — تسجيل التشخيص وحالة الأسنان لكل سطح بدقة متناهية (بيانات توضيحية افتراضية).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>حسابات المريض وسجل المدفوعات السريرية</h2>
          <p>يرتبط كل إجراء يتم توثيقه في المخطط مباشرة بالحساب المالي للمريض، مما يمنع نسيان إضافة أية تكلفة علاجية:</p>
          <ul class="prose-list">
            <li><strong>كشف حساب تفصيلي:</strong> عرض إجمالي تكلفة خطة العلاج، الخصومات الممنوحة، المبالغ المسددة، والمتبقي.</li>
            <li><strong>سندات قبض فورية:</strong> توثيق طرق الدفع (نقدي، تحويل بنكي، إلكتروني) وطباعة إيصال السداد للمريض.</li>
            <li><strong>تكامل سلس مع الاستقبال:</strong> يتيح لموظف الاستقبال معرفة المبلغ المطلوب تحصيله بدقة بمجرد خروج المريض من غرفة الكشف.</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/patients-ar.webp" width="1440" height="1000" alt="قائمة وسجلات ملفات المرضى في Dentix" loading="lazy">
          <figcaption>سجل ملفات المرضى في Dentix — بحث سريع والوصول الفوري للملف الشامل والمواعيد السابقة.</figcaption>
        </figure>

        <section class="prose-section">
          <h2>أمان وسرية السجلات الطبية</h2>
          <p>تخضع كافة السجلات الطبية في Dentix لحماية مشددة وفق أفضل معايير الأمان وعزل البيانات بين العيادات. للاطلاع على تدابير الأمان التفصيلية، يمكنك قراءة <a href="/ar/privacy" style="color: var(--color-primary-dark); font-weight: 700;">سياسة الخصوصية وأمن البيانات</a> أو استعراض <a href="/ar/appointments-finance" style="color: var(--color-primary-dark); font-weight: 700;">دليل تنظيم المواعيد وحسابات العيادة</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/dental-patient-records',
    hreflangAr: 'https://www.dentixs.app/ar/dental-patient-records',
    hreflangEn: 'https://www.dentixs.app/en/dental-patient-records',
    hreflangDefault: 'https://www.dentixs.app/ar/dental-patient-records',
    targetLangUrl: '/en/dental-patient-records',
    targetLangText: 'English',
    targetLangAria: 'Switch to English Dental Patient Records guide',
    targetLangCode: 'en',
    title: 'Dentix — إدارة ملفات مرضى الأسنان إلكترونيًا وسجلات العلاج',
    metaDescription: 'دليل شامل حول إدارة ملفات مرضى الأسنان إلكترونياً في Dentix: السجل الطبي، مخطط الأسنان السريري، جلسات علاج الجذور، وحسابات المريض.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/ar/dental-patient-records#webpage',
          'url': 'https://www.dentixs.app/ar/dental-patient-records',
          'headline': 'إدارة ملفات مرضى الأسنان إلكترونيًا وسجلات العلاج',
          'description': 'دليل إدارة ملفات مرضى الأسنان والسجلات الطبية ومخطط الأسنان السريري مع Dentix.',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'ملفات المرضى ومخطط الأسنان',
    contentHtml,
  });
}

function getPatientRecordsEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">Dental Patient Records Management: Secure Digital Charts & History</h1>
        <p class="legal-meta">Comprehensive guide to digital dental charts, patient medical history, endodontic sessions, and treatment tracking.</p>
        <p class="legal-intro">The patient health record is the clinical core of every dental practice. Dentix delivers a secure electronic dental record (EDR) that integrates comprehensive medical histories, interactive odontograms, and detailed session progress into a single streamlined system.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>The Clinical Value of Electronic Dental Records (EDR)</h2>
          <p>Dental treatments require millimeter-level precision and reliable historical documentation across multi-visit treatment plans. Dentix elevates clinical care standards by providing:</p>
          <ul class="prose-list">
            <li><strong>Medical Alert & Allergy Flags:</strong> Instant visibility of chronic conditions (cardiovascular issues, diabetes, hypertension) and drug/latex allergies upon opening any chart.</li>
            <li><strong>Chronological Clinical Visit Notes:</strong> Systematic documentation of clinical procedures, practitioner notes, and visit timestamps.</li>
            <li><strong>Diagnostic Radiograph & Document Storage:</strong> Direct attachment of periapical, panoramic, and bitewing X-rays alongside patient profiles.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Interactive Clinical Dental Charting (Odontogram)</h2>
          <p>Dentix features an intuitive visual odontogram covering adult and pediatric dental anatomy, empowering clinicians to:</p>
          <ul class="prose-list">
            <li>Examine and record conditions across individual tooth surfaces (Mesial, Distal, Occlusal, Buccal, Lingual).</li>
            <li>Differentiate pre-existing restorations, crowns, implants, and missing teeth from proposed treatments.</li>
            <li>Structure phased treatment plans matching patient urgency and financial capabilities.</li>
            <li>Document complex endodontic care sessions including working lengths, MAF file sizes, and taper measurements per canal.</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/chart-en.webp" width="1440" height="1000" alt="Interactive dental chart and odontogram in Dentix software" loading="lazy">
          <figcaption>Dentix Odontogram — Visual surface-level diagnostic charting and procedure planning (fictional demonstration data).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>Integrated Patient Treatment Ledger</h2>
          <p>Every clinical procedure scheduled or completed in the dental chart directly updates the patient's financial balance:</p>
          <ul class="prose-list">
            <li><strong>Transparent Ledger Balances:</strong> Real-time overview of treatment plan totals, discounts, settled payments, and remaining credit/debit balances.</li>
            <li><strong>Itemized Payment Receipts:</strong> Immediate generation of receipts with multiple payment methods (cash, card, bank transfer).</li>
            <li><strong>Reception Desk Alignment:</strong> Front-desk staff immediately see what to collect when the patient leaves the operatory room.</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/patients-en.webp" width="1440" height="1000" alt="Patient records search and profile in Dentix" loading="lazy">
          <figcaption>Dentix Patient Directory — Instant search, profile access, and comprehensive visit history.</figcaption>
        </figure>

        <section class="prose-section">
          <h2>Confidentiality and Strict Data Isolation</h2>
          <p>All clinical records in Dentix are safeguarded with strict tenant isolation and modern encryption. For detailed technical protections, read our <a href="/en/privacy" style="color: var(--color-primary-dark); font-weight: 700;">Privacy & Data Security Policy</a>, or review our guide on <a href="/en/appointments-finance" style="color: var(--color-primary-dark); font-weight: 700;">Appointment Scheduling & Clinic Finance</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/dental-patient-records',
    hreflangAr: 'https://www.dentixs.app/ar/dental-patient-records',
    hreflangEn: 'https://www.dentixs.app/en/dental-patient-records',
    hreflangDefault: 'https://www.dentixs.app/ar/dental-patient-records',
    targetLangUrl: '/ar/dental-patient-records',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى دليل ملفات مرضى الأسنان باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — Dental Patient Records Management: Secure Digital Charts & History',
    metaDescription: 'Complete guide to digital dental patient records: secure medical history, interactive odontogram charting, endodontic sessions, and patient ledger balances.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/en/dental-patient-records#webpage',
          'url': 'https://www.dentixs.app/en/dental-patient-records',
          'headline': 'Dental Patient Records Management: Secure Digital Charts & History',
          'description': 'Comprehensive guide on managing digital dental patient records, charts, and medical history with Dentix.',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'Patient Records & Charting',
    contentHtml,
  });
}

// 6. CONTENT PAGE 3: APPOINTMENTS & CLINIC FINANCE
function getAppointmentsFinanceAr() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">تنظيم مواعيد عيادة الأسنان وإدارة حساباتها ومصاريفها</h1>
        <p class="legal-meta">كيفية إدارة جدول المواعيد، متابعة قائمة الانتظار، تحصيل مستحقات العلاج، وضبط تكاليف المعامل ومصروفات العيادة.</p>
        <p class="legal-intro">يعتمد نجاح عيادة الأسنان على التوازن بين الانضباط السريري والكفاءة التشغيلية والمالية. يقدم Dentix أدوات متكاملة لإدارة جدول المواعيد اليومي، وقوائم المتابعة، والتقارير المالية الدقيقة التي تبين صافي حركة العيادة.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>إدارة جدول المواعيد وقائمة الانتظار اليومية</h2>
          <p>يساعد جدول مواعيد Dentix على تقليل أوقات الانتظار ومنع التضارب بين غرف الكشف وأطباء العيادة:</p>
          <ul class="prose-list">
            <li><strong>تتبع حالات الحجز الحية:</strong> يوضح الجدول حالة كل مريض (محجوز، تم التأكيد، حضر إلى الاستقبال، داخل غرفة العلاج، انتهت الزيارة، أو ملغي).</li>
            <li><strong>قائمة الانتظار السريعة:</strong> تنظيم ترتيب دخول المرضى إلى العيادة ومنع تكدس صالة الاستقبال.</li>
            <li><strong>قائمة المتابعة والجلسات القادمة:</strong> حصر المرضى الذين يحتاجون إلى جلسات تالية لحشو العصب أو مقاسات التركيبات وإعادة جدولتها بسهولة.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>الإدارة المالية الشاملة لعيادة الأسنان</h2>
          <p>تختلف مالية عيادات الأسنان عن الأنشطة الأخرى لاشتمالها على فترات علاج طويلة وتكاليف معامل خارجية ومواد باهظة الثمن. يوفر Dentix رقابة مالية دقيقة من خلال:</p>
          <ul class="prose-list">
            <li><strong>فواتير العلاج وسندات القبض:</strong> إصدار فواتير واضحة تبين تفاصيل الخدمات الطبية المقدمة والمبالغ المدفوعة.</li>
            <li><strong>أرصدة المرضى والمديونيات:</strong> معرفة المبالغ المتبقية على المرضى بدقة، مما يساعد الاستقبال على تحصيل المستحقات في كل زيارة.</li>
            <li><strong>متابعة تكاليف ومعامل الأسنان:</strong> تسجيل طلبات المعامل (التركيبات، التيجان، التقويم) وتكاليفها وحساب ديون المعامل بدقة لمنع التداخل المالي.</li>
            <li><strong>مصروفات العيادة التشغيلية:</strong> تدوين بنود الصرف اليومية (مواد الحشو، التعقيم، الإيجار، الفواتير) لمقارنة الإيرادات بالمصروفات.</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/dashboard-ar.webp" width="1440" height="1000" alt="لوحة تقارير المواعيد والإيرادات المالية في Dentix" loading="lazy">
          <figcaption>Dentix — متابعة الإيرادات وحالات المواعيد اليومية بوضوح تام لاتخاذ القرارات الإدارية المناسبة (بيانات توضيحية افتراضية).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>التقارير اليومية والشهرية لاتخاذ القرار</h2>
          <p>يوفر النظام تقارير تلخص أداء العيادة، بما في ذلك:</p>
          <ul class="prose-list">
            <li>إجمالي الإيرادات المحصلة حسب وسيلة الدفع (نقدي، تحويل، بطاقة).</li>
            <li>صافي الدخل بعد خصم المصروفات التشغيلية ومستحقات المعامل.</li>
            <li>نسبة التزام المرضى بالمواعيد ومعدلات الحضور والإلغاء.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>ابدأ بتنظيم مواعيد وحسابات عيادتك</h2>
          <p>انضم إلى عيادات الأسنان التي تنظم عملياتها اليومية مع Dentix. يمكنك البدء عبر <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">إنشاء حساب عيادة</a>، أو الاطلاع على <a href="/ar/plans" style="color: var(--color-primary-dark); font-weight: 700;">باقات الاشتراك والأسعار</a>، أو التواصل معنا عبر <a href="/ar/contact" style="color: var(--color-primary-dark); font-weight: 700;">صفحة الدعم والمبيعات</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'ar',
    dir: 'rtl',
    canonicalUrl: 'https://www.dentixs.app/ar/appointments-finance',
    hreflangAr: 'https://www.dentixs.app/ar/appointments-finance',
    hreflangEn: 'https://www.dentixs.app/en/appointments-finance',
    hreflangDefault: 'https://www.dentixs.app/ar/appointments-finance',
    targetLangUrl: '/en/appointments-finance',
    targetLangText: 'English',
    targetLangAria: 'Switch to English Appointments & Finance guide',
    targetLangCode: 'en',
    title: 'Dentix — تنظيم مواعيد عيادة الأسنان وإدارة حساباتها ومصاريفها',
    metaDescription: 'دليل عملي حول تنظيم جدول مواعيد عيادات الأسنان، إدارة قائمة الانتظار، تحصيل الفواتير، ومتابعة مصاريف المعامل مع Dentix.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/ar/appointments-finance#webpage',
          'url': 'https://www.dentixs.app/ar/appointments-finance',
          'headline': 'تنظيم مواعيد عيادة الأسنان وإدارة حساباتها ومصاريفها',
          'description': 'دليل إدارة مواعيد عيادة الأسنان، قائمة الانتظار، فواتير العلاج، وتكاليف المعامل مع Dentix.',
          'inLanguage': 'ar',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'المواعيد والحسابات',
    contentHtml,
  });
}

function getAppointmentsFinanceEn() {
  const contentHtml = `
      <header class="legal-header">
        <h1 class="legal-title">Dental Appointments & Clinic Financial Management</h1>
        <p class="legal-meta">Organizing operatory schedules, managing patient queues, collecting balances, and monitoring laboratory costs.</p>
        <p class="legal-intro">Practice success depends on clinical excellence paired with reliable operational efficiency and clear financial tracking. Dentix provides comprehensive tools to manage daily bookings, recall workflows, patient invoices, and clinic expense ledgers.</p>
      </header>

      <article class="legal-article">
        <section class="prose-section">
          <h2>Streamlined Appointment Books & Daily Waiting Queues</h2>
          <p>Dentix appointment scheduling reduces patient wait times and eliminates friction between the reception desk and operatory rooms:</p>
          <ul class="prose-list">
            <li><strong>Live Appointment Statuses:</strong> Track each visit status in real time (Scheduled, Confirmed, Arrived/Waiting, In Chair, Completed, Cancelled).</li>
            <li><strong>Front-Desk Waiting Queue:</strong> Direct visibility of seated patients to maintain orderly, timely patient transitions.</li>
            <li><strong>Recall & Multi-Visit Follow-Up Queues:</strong> Automatically track patients needing multi-visit endodontic sessions, crown cementation, or periodic hygiene recalls.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Comprehensive Practice Financial Controls</h2>
          <p>Dental finances require specialized accounting to handle multi-stage clinical treatments, external lab fees, and consumable material costs:</p>
          <ul class="prose-list">
            <li><strong>Procedure Invoicing & Payment Receipts:</strong> Immediate generation of itemized receipts detailing treatments rendered and amounts received.</li>
            <li><strong>Outstanding Patient Balances:</strong> Accurate ledger tracking of remaining patient debt, facilitating prompt collection upon each visit.</li>
            <li><strong>Dental Lab Order & Cost Reconciliation:</strong> Track laboratory orders (crowns, bridges, prosthetics) and log technician dues to prevent financial discrepancies.</li>
            <li><strong>Clinic Operational Overhead Logging:</strong> Document daily expenses (disposables, sterilization materials, rent, utilities) for transparent net margin calculations.</li>
          </ul>
        </section>

        <figure class="content-figure">
          <img src="/marketing/screens/dashboard-en.webp" width="1440" height="1000" alt="Dentix financial reporting and appointment dashboard" loading="lazy">
          <figcaption>Dentix Management Dashboard — Track revenue streams, appointment volumes, and clinic expenses with ease (fictional demonstration data).</figcaption>
        </figure>

        <section class="prose-section">
          <h2>Actionable Reporting for Practice Growth</h2>
          <p>The platform compiles regular management summaries, including:</p>
          <ul class="prose-list">
            <li>Total revenue collections categorized by payment method (cash, card, bank transfer).</li>
            <li>Net practice income after deducting clinic operating expenses and technician costs.</li>
            <li>Patient attendance metrics, cancellation rates, and operatory chair utilization.</li>
          </ul>
        </section>

        <section class="prose-section">
          <h2>Take Control of Your Clinic Today</h2>
          <p>Join dental practices organizing their workflows with Dentix. Start immediately by <a href="/register" style="color: var(--color-primary-dark); font-weight: 700;">Creating a Clinic Account</a>, review our <a href="/en/plans" style="color: var(--color-primary-dark); font-weight: 700;">Subscription Plans</a>, or reach out on our <a href="/en/contact" style="color: var(--color-primary-dark); font-weight: 700;">Contact & Support page</a>.</p>
        </section>
      </article>
  `;

  return renderBaseLayout({
    lang: 'en',
    dir: 'ltr',
    canonicalUrl: 'https://www.dentixs.app/en/appointments-finance',
    hreflangAr: 'https://www.dentixs.app/ar/appointments-finance',
    hreflangEn: 'https://www.dentixs.app/en/appointments-finance',
    hreflangDefault: 'https://www.dentixs.app/ar/appointments-finance',
    targetLangUrl: '/ar/appointments-finance',
    targetLangText: 'العربية',
    targetLangAria: 'التبديل إلى دليل المواعيد والحسابات باللغة العربية',
    targetLangCode: 'ar',
    title: 'Dentix — Dental Appointments & Clinic Financial Management',
    metaDescription: 'Practical guide to managing dental clinic appointments, waiting queues, procedure billing, and lab expenses with Dentix cloud software.',
    structuredData: {
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
          '@type': 'Article',
          '@id': 'https://www.dentixs.app/en/appointments-finance#webpage',
          'url': 'https://www.dentixs.app/en/appointments-finance',
          'headline': 'Dental Appointments & Clinic Financial Management',
          'description': 'Comprehensive guide on dental clinic appointments, queues, invoices, and lab expense tracking.',
          'inLanguage': 'en',
          'isPartOf': {
            '@type': 'WebSite',
            '@id': 'https://www.dentixs.app/#website',
            'url': 'https://www.dentixs.app',
            'name': 'Dentix',
          },
        },
      ],
    },
    breadcrumbName: 'Appointments & Finance',
    contentHtml,
  });
}

export function generateAllContentPages(outputBaseDir = null) {
  const baseDir = outputBaseDir || path.join(frontendRoot, 'public');

  const pages = [
    // 1. About
    { path: 'ar/about/index.html', html: getAboutAr() },
    { path: 'en/about/index.html', html: getAboutEn() },
    // 2. Contact
    { path: 'ar/contact/index.html', html: getContactAr() },
    { path: 'en/contact/index.html', html: getContactEn() },
    // 3. Plans
    { path: 'ar/plans/index.html', html: getPlansAr() },
    { path: 'en/plans/index.html', html: getPlansEn() },
    // 4. Dental Clinic Management Software
    { path: 'ar/dental-clinic-management-software/index.html', html: getClinicSoftwareAr() },
    { path: 'en/dental-clinic-management-software/index.html', html: getClinicSoftwareEn() },
    // 5. Dental Patient Records
    { path: 'ar/dental-patient-records/index.html', html: getPatientRecordsAr() },
    { path: 'en/dental-patient-records/index.html', html: getPatientRecordsEn() },
    // 6. Appointments & Finance
    { path: 'ar/appointments-finance/index.html', html: getAppointmentsFinanceAr() },
    { path: 'en/appointments-finance/index.html', html: getAppointmentsFinanceEn() },
  ];

  for (const p of pages) {
    const fullPath = path.join(baseDir, p.path);
    mkdirSync(path.dirname(fullPath), { recursive: true });
    writeFileSync(fullPath, p.html, 'utf8');
    console.log(`[generate-content-pages] Wrote ${p.path}`);
  }
}

// Run if CLI
const isCli = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isCli) {
  generateAllContentPages(process.argv[2]);
}
