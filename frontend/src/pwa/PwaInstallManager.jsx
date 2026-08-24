import { useTranslation } from 'react-i18next';
import { useRegisterSW } from 'virtual:pwa-register/react';
import { Share, PlusSquare } from 'lucide-react';
import { usePwaInstall } from './usePwaInstall';

/**
 * Platform-aware PWA install manager + user-controlled update prompt.
 * Replaces the narrow Chromium-only InstallPrompt (plan §9.1–§9.3).
 */
export function PwaInstallManager() {
  const { t } = useTranslation();
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();
  const {
    platform,
    canPrompt,
    androidPromptReady,
    iosInstructionsRelevant,
    promptInstall,
    dismiss,
  } = usePwaInstall();

  if (needRefresh) {
    return (
      <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] start-4 end-4 md:start-auto md:end-4 md:w-80
                      bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4 z-50
                      border border-gray-200 dark:border-gray-700"
           role="status">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
          {t('pwa.update.title')}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {t('pwa.update.description')}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => updateServiceWorker(true)}
            className="flex-1 bg-blue-600 text-white text-sm rounded-lg py-2
                       hover:bg-blue-700 transition-colors"
          >
            {t('pwa.update.confirm')}
          </button>
          <button
            type="button"
            onClick={() => setNeedRefresh(false)}
            className="flex-1 bg-gray-100 dark:bg-gray-700 text-gray-700
                       dark:text-gray-300 text-sm rounded-lg py-2
                       hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            {t('pwa.update.later')}
          </button>
        </div>
      </div>
    );
  }

  if (!canPrompt) return null;

  if (platform === 'ios' && iosInstructionsRelevant) {
    return (
      <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] start-4 end-4 md:hidden
                      bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4 z-50
                      border border-gray-200 dark:border-gray-700"
           role="dialog"
           aria-label={t('pwa.install.ios.title')}>
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-3">
          {t('pwa.install.ios.title')}
        </p>
        <ol className="text-xs text-gray-500 dark:text-gray-400 space-y-2 mb-3 list-decimal ps-4">
          <li className="flex items-center gap-1">
            <Share size={12} className="inline flex-shrink-0" aria-hidden="true" />
            {t('pwa.install.ios.step1')}
          </li>
          <li>{t('pwa.install.ios.step2')}</li>
          <li>{t('pwa.install.ios.step3')}</li>
          <li className="flex items-center gap-1">
            <PlusSquare size={12} className="inline flex-shrink-0" aria-hidden="true" />
            {t('pwa.install.ios.step4')}
          </li>
        </ol>
        <button
          type="button"
          onClick={dismiss}
          className="w-full bg-gray-100 dark:bg-gray-700 text-gray-700
                     dark:text-gray-300 text-sm rounded-lg py-2
                     hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          {t('pwa.install.ios.action')}
        </button>
      </div>
    );
  }

  if (androidPromptReady) {
    return (
      <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] start-4 end-4 md:start-auto md:end-4 md:w-80
                      bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4 z-50
                      border border-gray-200 dark:border-gray-700">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
          {t('pwa.install.title')}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {t('pwa.install.description')}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={promptInstall}
            className="flex-1 bg-blue-600 text-white text-sm rounded-lg py-2
                       hover:bg-blue-700 transition-colors"
          >
            {t('pwa.install.action')}
          </button>
          <button
            type="button"
            onClick={dismiss}
            className="flex-1 bg-gray-100 dark:bg-gray-700 text-gray-700
                       dark:text-gray-300 text-sm rounded-lg py-2
                       hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            {t('pwa.install.later')}
          </button>
        </div>
      </div>
    );
  }

  return null;
}
