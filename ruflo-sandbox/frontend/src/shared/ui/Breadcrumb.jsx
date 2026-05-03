import { ChevronRight, ChevronLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Breadcrumb({ items }) {
    const { i18n } = useTranslation();
    const isRtl = i18n.language === 'ar' || document.documentElement.dir === 'rtl';
    const Separator = isRtl ? ChevronLeft : ChevronRight;

    return (
        <nav aria-label="breadcrumb" className="mb-4">
            <ol className="flex items-center space-x-2 rtl:space-x-reverse text-sm font-medium">
                {items.map((item, index) => {
                    const isLast = index === items.length - 1;

                    return (
                        <li key={index} className="flex items-center space-x-2 rtl:space-x-reverse">
                            {index > 0 && <Separator className="w-4 h-4 text-slate-400 mx-1" />}
                            
                            {item.to && !isLast ? (
                                <Link 
                                    to={item.to} 
                                    className="text-primary hover:text-primary-600 transition-colors"
                                >
                                    {item.label}
                                </Link>
                            ) : (
                                <span className={`text-slate-500 ${isLast ? 'font-bold text-slate-800 dark:text-white' : ''}`}>
                                    {item.label}
                                </span>
                            )}
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}
