import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PropTypes from 'prop-types';
import { buildAttachmentUrl } from '../attachmentUtils';

export default function ProtectedImage({
    filePath,
    thumbnail = false,
    alt,
    className,
    onClick,
    storageStatus = 'ready',
    retryGeneration = 0,
    ...rest
}) {
    const { t } = useTranslation();
    const [unavailable, setUnavailable] = useState(false);
    const [manualRetryCount, setManualRetryCount] = useState(0);

    useEffect(() => {
        setUnavailable(false);
    }, [filePath, thumbnail, storageStatus, retryGeneration, manualRetryCount]);

    let src = buildAttachmentUrl(filePath);
    if (thumbnail && src.includes('/api/v1/upload/drive/')) src += '?variant=thumbnail';

    if (storageStatus === 'pending') {
        return (
            <div
                {...rest}
                role="status"
                aria-label={t('backup.image_pending')}
                className={`${className || ''} flex flex-col items-center justify-center bg-slate-100 p-2 text-center text-xs text-slate-500`}
            >
                <span className="animate-pulse">{t('backup.image_pending')}</span>
            </div>
        );
    }

    if (unavailable || !src) {
        return (
            <div
                {...rest}
                role="img"
                aria-label={t('backup.image_unavailable')}
                className={`${className || ''} flex flex-col items-center justify-center bg-slate-100 p-2 text-center text-xs text-slate-600`}
            >
                <span>{t('backup.image_unavailable')}</span>
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        setUnavailable(false);
                        setManualRetryCount((prev) => prev + 1);
                    }}
                    className="mt-1 text-[11px] text-primary-600 hover:underline cursor-pointer"
                >
                    {t('common.retry', 'إعادة المحاولة')}
                </button>
            </div>
        );
    }

    return (
        <img
            {...rest}
            key={`${src}-${retryGeneration}-${manualRetryCount}`}
            src={src}
            alt={alt}
            className={className}
            loading={thumbnail ? 'lazy' : undefined}
            onClick={onClick}
            onError={() => setUnavailable(true)}
        />
    );
}

ProtectedImage.propTypes = {
    filePath: PropTypes.string,
    thumbnail: PropTypes.bool,
    alt: PropTypes.string,
    className: PropTypes.string,
    onClick: PropTypes.func,
    storageStatus: PropTypes.string,
    retryGeneration: PropTypes.number,
};
