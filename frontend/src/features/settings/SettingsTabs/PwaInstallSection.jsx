import { useTranslation } from 'react-i18next';
import { Download, Smartphone } from 'lucide-react';
import { usePwaInstall } from '@/pwa/usePwaInstall';

/**
 * Permanent "Install Dentix" entry in Settings (plan §9.2).
 * Always available when the platform supports installation, independent of
 * the banner dismissal cooldown.
 */
export default function PwaInstallSection() {
    const { t } = useTranslation();
    const {
        standalone,
        installed,
        androidPromptReady,
        iosInstructionsRelevant,
        promptInstall,
    } = usePwaInstall();

    if (standalone || installed) {
        return (
            <div className="p-6 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-100 dark:border-emerald-500/10 mb-4">
                <div className="flex items-center gap-3 text-emerald-600 dark:text-emerald-400 mb-1">
                    <Smartphone size={20} />
                    <span className="font-bold">{t('settings.pwa.install_installed')}</span>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    {t('settings.pwa.install_installed_hint')}
                </p>
            </div>
        );
    }

    const canInstallHere = androidPromptReady || iosInstructionsRelevant;
    if (!canInstallHere) return null;

    return (
        <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5 mb-4">
            <div className="flex items-center gap-3 text-slate-500 mb-2">
                <Download size={20} />
                <span className="font-bold">{t('settings.pwa.install_title')}</span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                {iosInstructionsRelevant
                    ? t('settings.pwa.install_ios_hint')
                    : t('settings.pwa.install_description')}
            </p>
            {androidPromptReady && (
                <button
                    type="button"
                    onClick={promptInstall}
                    className="bg-blue-600 text-white text-sm rounded-lg px-4 py-2
                               hover:bg-blue-700 transition-colors"
                >
                    {t('settings.pwa.install_action')}
                </button>
            )}
        </div>
    );
}
