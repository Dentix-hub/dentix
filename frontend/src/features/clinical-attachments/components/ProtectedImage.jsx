import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PropTypes from 'prop-types';
import { buildAttachmentUrl } from '../attachmentUtils';

export default function ProtectedImage({ filePath, thumbnail = false, alt, className, onClick, ...rest }) {
    const { t } = useTranslation();
    const [unavailable, setUnavailable] = useState(false);
    useEffect(() => setUnavailable(false), [filePath, thumbnail]);
    let src = buildAttachmentUrl(filePath);
    if (thumbnail && src.includes('/api/v1/upload/drive/')) src += '?variant=thumbnail';
    if (unavailable || !src) {
        return <div {...rest} role="img" aria-label={t('backup.image_unavailable')} className={`${className || ''} flex items-center justify-center bg-slate-100 p-2 text-center text-xs text-slate-600`}>{t('backup.image_unavailable')}</div>;
    }
    return <img {...rest} src={src} alt={alt} className={className} loading={thumbnail ? 'lazy' : undefined} onClick={onClick} onError={() => setUnavailable(true)} />;
}

ProtectedImage.propTypes = {
    filePath: PropTypes.string,
    thumbnail: PropTypes.bool,
    alt: PropTypes.string,
    className: PropTypes.string,
    onClick: PropTypes.func,
};
