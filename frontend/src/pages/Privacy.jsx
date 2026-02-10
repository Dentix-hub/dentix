import { ArrowRight, Lock, Eye, Server, UserCheck, Shield, MessageCircle, AlertTriangle, FileText, Database } from 'lucide-react';
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

export default function Privacy() {
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
                    <span>{t('static.privacy.back')}</span>
                </button>

                <div className="text-center mb-12">
                    <h1 className="text-3xl md:text-4xl font-black text-text-primary mb-4">{t('static.privacy.title')}</h1>
                    <p className="text-text-secondary text-lg">{t('static.privacy.last_updated')}</p>
                    <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
                        {t('static.privacy.intro')}
                    </p>
                </div>

                <div className="space-y-6">
                    <Section title={t('static.privacy.sections.1.title')} icon={FileText}>
                        <p>{t('static.privacy.sections.1.intro')}</p>

                        <div className="mt-4 space-y-4">
                            <div>
                                <strong className="text-text-primary">{t('static.privacy.sections.1.clinic.title')}</strong>
                                <ul className="list-disc list-inside mt-1 mr-4">
                                    {(t('static.privacy.sections.1.clinic.items', { returnObjects: true }) || []).map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>

                            <div>
                                <strong className="text-text-primary">{t('static.privacy.sections.1.users.title')}</strong>
                                <ul className="list-disc list-inside mt-1 mr-4">
                                    {(t('static.privacy.sections.1.users.items', { returnObjects: true }) || []).map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>

                            <div>
                                <strong className="text-text-primary">{t('static.privacy.sections.1.patients.title')}</strong>
                                <ul className="list-disc list-inside mt-1 mr-4">
                                    {(t('static.privacy.sections.1.patients.items', { returnObjects: true }) || []).map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </Section>

                    <Section title={t('static.privacy.sections.2.title')} icon={props => <Shield className="text-primary w-6 h-6" />}>
                        <p>{t('static.privacy.sections.2.intro')}</p>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                            {(t('static.privacy.sections.2.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>

                    <Section title={t('static.privacy.sections.3.title')} icon={Lock}>
                        <p>{t('static.privacy.sections.3.intro')}</p>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                            {(t('static.privacy.sections.3.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>

                    <Section title={t('static.privacy.sections.4.title')} icon={Server}>
                        <p>{t('static.privacy.sections.4.intro')}</p>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                            {(t('static.privacy.sections.4.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                        <div className="mt-4 p-4 bg-primary/5 rounded-xl border border-primary/10">
                            <strong>{t('static.privacy.sections.4.alert')}</strong>
                        </div>
                    </Section>

                    <Section title={t('static.privacy.sections.5.title')} icon={Eye}>
                        <p>{t('static.privacy.sections.5.content')}</p>
                    </Section>

                    <Section title={t('static.privacy.sections.6.title')} icon={Database}>
                        <p>{t('static.privacy.sections.6.content')}</p>
                    </Section>

                    <Section title={t('static.privacy.sections.7.title')} icon={UserCheck}>
                        <p>{t('static.privacy.sections.7.intro')}</p>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                            {(t('static.privacy.sections.7.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Section>

                    <Section title={t('static.privacy.sections.8.title')} icon={AlertTriangle}>
                        <p>{t('static.privacy.sections.8.content')}</p>
                    </Section>

                    <Section title={t('static.privacy.sections.9.title')} icon={Database}>
                        <p>{t('static.privacy.sections.9.intro')}</p>
                        <ul className="list-disc list-inside mt-2 mb-2 space-y-1">
                            {(t('static.privacy.sections.9.items', { returnObjects: true }) || []).map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                        <p>{t('static.privacy.sections.9.outro')}</p>
                    </Section>

                    <Section title={t('static.privacy.sections.10.title')} icon={FileText}>
                        <p>{t('static.privacy.sections.10.content')}</p>
                    </Section>

                    <Section title={t('static.privacy.sections.11.title')} icon={MessageCircle}>
                        <p>{t('static.privacy.sections.11.content')}</p>
                    </Section>
                </div>

                <div className="mt-12 text-center text-text-secondary text-sm">
                    &copy; 2026 DENTIX. {t('common.all_rights_reserved')}
                </div>
            </div>
        </div>
    );
}