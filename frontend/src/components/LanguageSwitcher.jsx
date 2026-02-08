import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui';
import { Globe } from 'lucide-react';

const LanguageSwitcher = () => {
    const { t, i18n } = useTranslation();

    // Effect to update document direction when language changes
    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr';
        document.documentElement.lang = i18n.language;
    }, [i18n.language]);

    const toggleLanguage = () => {
        const newLang = i18n.language === 'ar' ? 'en' : 'ar';
        i18n.changeLanguage(newLang);
    };

    return (
        <Button
            variant="ghost"
            size="sm"
            onClick={toggleLanguage}
            className="w-full justify-start gap-3 hover:bg-surface-hover text-text-secondary hover:text-primary transition-colors duration-200"
        >
            <Globe size={18} />
            <span className="font-medium text-sm">
                {i18n.language === 'ar' ? 'English' : 'العربية'}
            </span>
        </Button>
    );
};

export default LanguageSwitcher;
