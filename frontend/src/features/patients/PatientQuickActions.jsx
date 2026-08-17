import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Home, Plus, Users } from 'lucide-react';
import { Button, PageHeader } from '@/shared/ui';

export default memo(function PatientQuickActions({ onAddClick }) {
    const { t } = useTranslation();

    return (
        <PageHeader
            title={t('patients.title')}
            subtitle={t('patients.workspace_subtitle', 'Find the right patient quickly and continue the next clinic action.')}
            icon={Users}
            breadcrumbs={[
                { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                { label: t('patients.title') },
            ]}
            actions={
                <Button onClick={onAddClick} size="lg">
                    <Plus className="w-4 h-4 me-2" />
                    {t('patients.add_new')}
                </Button>
            }
        />
    );
});
