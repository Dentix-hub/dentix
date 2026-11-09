import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { describe, expect, it } from 'vitest';
import { CURRENT_ACTIVE_INDEXABLE_ROUTES } from '../../scripts/routeInventory.mjs';

describe('Commercial publication remains blocked without runtime plan evidence', () => {
    it.each(['ar', 'en'])('keeps %s subscription inquiries useful without publishing unverified offers', lang => {
        const doc = new JSDOM(readFileSync(`public/${lang}/plans/index.html`, 'utf8')).window.document;
        const text = [doc.title, ...Array.from(doc.querySelectorAll('meta[content]'), meta => meta.getAttribute('content')), doc.querySelector('main').textContent].join(' ');
        expect(doc.querySelectorAll('.plan-price, .plan-card')).toHaveLength(0);
        expect(text).not.toMatch(/\b(?:200|400|1000)\b|EGP|ج\.م/);
        expect(text).not.toMatch(/Essential|Professional|Business|14.day|14 يوم|free trial|تجربة مجانية/i);
        expect(doc.querySelector('link[rel="canonical"]').getAttribute('href')).toBe(`https://www.dentixs.app/${lang}/plans`);
        expect(doc.querySelector('main a[href="https://wa.me/201010285288"]')).not.toBeNull();
        expect(doc.querySelector('main a[href="mailto:smartsentalclinicapp@gmail.com"]')).not.toBeNull();
        for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
            const schema = JSON.stringify(JSON.parse(script.textContent));
            expect(schema).not.toMatch(/"offers"|"price"|"priceCurrency"|"Offer"/);
        }
    });

    it('omits unsupported plan popularity, multi-branch, support-priority and chair-utilization claims', () => {
        for (const url of CURRENT_ACTIVE_INDEXABLE_ROUTES) {
            const doc = new JSDOM(readFileSync(`public${new URL(url).pathname}/index.html`, 'utf8')).window.document;
            expect(doc.querySelector('main').textContent, url).not.toMatch(/فروع متعددة|الأكثر طلباً|أولوية قصوى|التأهيل الميداني|Most Popular|Priority onboarding|operatory chair utilization/i);
        }
    });
});
