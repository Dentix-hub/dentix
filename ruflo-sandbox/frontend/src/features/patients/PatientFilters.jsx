import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';
import { Input } from '@/shared/ui';

export default memo(function PatientFilters({ search, onSearchChange }) {
    const { t } = useTranslation();

    return (
        <div className="sticky top-0 z-10 bg-slate-50/80 backdrop-blur-sm py-3">
            <Input
                type="text"
                placeholder={t('patients.search_placeholder')}
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                icon={Search}
                containerClassName="max-w-md"
                dir="auto"
            />
        </div>
    );
});

