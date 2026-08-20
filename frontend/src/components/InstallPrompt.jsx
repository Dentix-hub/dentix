import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useRegisterSW } from 'virtual:pwa-register/react';

export function InstallPrompt() {
  const { t } = useTranslation();
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowPrompt(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') setShowPrompt(false);
    setDeferredPrompt(null);
  };

  if (needRefresh) {
    return (
      <div className="fixed bottom-4 start-4 end-4 md:start-auto md:end-4 md:w-80
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

  if (!showPrompt) return null;

  return (
    <div className="fixed bottom-4 start-4 end-4 md:start-auto md:end-4 md:w-80
                    bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4 z-50
                    border border-gray-200 dark:border-gray-700">
      <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
        ثبّت DENTIX على جهازك
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        وصول سريع بدون متصفح
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleInstall}
          className="flex-1 bg-blue-600 text-white text-sm rounded-lg py-2
                     hover:bg-blue-700 transition-colors"
        >
          تثبيت
        </button>
        <button
          type="button"
          onClick={() => setShowPrompt(false)}
          className="flex-1 bg-gray-100 dark:bg-gray-700 text-gray-700
                     dark:text-gray-300 text-sm rounded-lg py-2
                     hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          لاحقاً
        </button>
      </div>
    </div>
  );
}
