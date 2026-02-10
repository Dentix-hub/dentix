import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getToken } from '@/utils';

const PriceListSelector = ({ value, onChange }) => {
    const { t } = useTranslation();
    const [lists, setLists] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!getToken()) {
            setLoading(false);
            return;
        }
        import('@/api').then(({ getPriceLists }) => {
            getPriceLists()
                .then(res => {
                    setLists(res.data || []);
                })
                .catch(() => {
                    // 401 or other error: keep lists empty, user can still use "Default"
                    setLists([]);
                })
                .finally(() => setLoading(false));
        });
    }, []);

    if (loading) return <div className="text-sm text-gray-400">{t('common.loading')}</div>;

    const valueStr = value === null || value === undefined ? '' : String(value);

    return (
        <select
            value={valueStr}
            onChange={e => {
                const v = e.target.value;
                onChange(v ? parseInt(v, 10) : null);
            }}
            className="w-full p-3 bg-white rounded-xl outline-none border border-gray-200 focus:border-blue-500"
        >
            <option value="">{t('patient_details.edit_modal.default_option')}</option>
            {Array.isArray(lists) && lists.map(l => (
                <option key={l.id} value={String(l.id)}>
                    {l.name} {l.type === 'insurance' ? t('patient_details.edit_modal.insurance_tag') : ''}
                </option>
            ))}
        </select>
    );
};

export default PriceListSelector;
