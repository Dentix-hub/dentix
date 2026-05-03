import { ArrowRight, Shield, Scale, AlertCircle, FileText, Lock, Globe, Server, MessageCircle, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
const Section = ({ title, children, icon: Icon }) => (
    <div className="bg-surface p-6 rounded-2xl border border-border mb-6">
        <div className="flex items-center gap-3 mb-4">
            {Icon && <Icon className="text-primary w-6 h-6" />}
            <h2 className="text-xl font-bold text-text-primary">{title}</h2>
        </div>
        <div className="text-text-secondary leading-relaxed space-y-2 text-sm md:text-base">
            {children}
        </div>
    </div>
);
export default function Terms() {
    const navigate = useNavigate();
    const { t } = useTranslation();
    return (
        <div className="min-h-screen bg-background p-6 md:p-12 font-sans text-right" dir="rtl">
            <div className="max-w-4xl mx-auto">
                <button
                    onClick={() => navigate(-1)}
                    className="flex items-center gap-2 text-text-secondary hover:text-primary mb-8 transition-colors font-bold"
                >
                    <ArrowRight size={20} />
                    <span>{t('static.terms.back')}</span>
                </button>
                <div className="text-center mb-12">
                    <h1 className="text-3xl md:text-4xl font-black text-text-primary mb-4">{t('static.terms.title')}</h1>
                    <p className="text-text-secondary text-lg">{t('static.terms.last_updated')}</p>
                    <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
                        {t('static.terms.intro')}
                    </p>
                </div>
                <div className="space-y-6">
                    <Section title={t('static.terms.sections.1.title')} icon={FileText}>
                        <p>{t('static.terms.sections.1.content')}</p>
                    </Section>
                    <Section title={t('static.terms.sections.2.title')} icon={Lock}>
                        <ul className="list-disc list-inside space-y-2">
                            {(t('static.terms.sections.2.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.3.title')} icon={Server}>
                        <ul className="list-disc list-inside space-y-2">
                            {(t('static.terms.sections.3.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.4.title')} icon={Shield}>
                        <p>{t('static.terms.sections.4.intro')}</p>
                        <ul className="list-disc list-inside space-y-1 mt-2 mb-2">
                            {(t('static.terms.sections.4.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                        <p>{t('static.terms.sections.4.outro')}</p>
                    </Section>
                    <Section title={t('static.terms.sections.5.title')} icon={RefreshCw}>
                        <ul className="list-disc list-inside space-y-2">
                            {(t('static.terms.sections.5.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.6.title')} icon={AlertCircle}>
                        <p>{t('static.terms.sections.6.content')}</p>
                    </Section>
                    <Section title={t('static.terms.sections.7.title')} icon={RefreshCw}>
                        <p>{t('static.terms.sections.7.intro')}</p>
                        <ul className="list-disc list-inside space-y-2 mt-2">
                            {(t('static.terms.sections.7.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.8.title')} icon={Globe}>
                        <p>{t('static.terms.sections.8.intro')}</p>
                        <ul className="list-disc list-inside space-y-1 mt-2">
                            {(t('static.terms.sections.8.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.9.title')} icon={AlertCircle}>
                        <p>{t('static.terms.sections.9.intro')}</p>
                        <ul className="list-disc list-inside space-y-1 mt-2">
                            {(t('static.terms.sections.9.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>
                    <Section title={t('static.terms.sections.10.title')} icon={Scale}>
                        <p>{t('static.terms.sections.10.content')}</p>
                    </Section>
                    <Section title={t('static.terms.sections.11.title')} icon={Scale}>
                        <p>{t('static.terms.sections.11.content')}</p>
                    </Section>
                    <Section title={t('static.terms.sections.12.title')} icon={MessageCircle}>
                        <p>{t('static.terms.sections.12.content')}</p>
                    </Section>
                </div>
                <div className="mt-12 text-center text-text-secondary text-sm">
                    &copy; 2026 DENTIX. {t('common.all_rights_reserved')}
                </div>
            </div>
        </div>
    );
}
