import { Ghost } from 'lucide-react';
const EmptyState = ({
    title = 'لا يوجد بيانات',
    description = 'لم يتم العثور على أي بيانات لعرضها هنا.',
    icon: Icon = Ghost,
    action,
    className = ''
}) => {
    return (
        <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
            <div className="bg-slate-100 dark:bg-slate-800/50 p-4 rounded-full mb-4 ring-8 ring-slate-50 dark:ring-slate-800/20">
                {typeof Icon === 'function' ? (
                    <Icon size={32} className="text-slate-400 dark:text-slate-500" />
                ) : (
                    Icon
                )}
            </div>
            <h3 className="text-lg font-bold text-text-primary mb-2">
                {title}
            </h3>
            <p className="text-text-secondary max-w-sm mb-6 text-sm leading-relaxed">
                {description}
            </p>
            {action && (
                <div className="mt-2">
                    {action}
                </div>
            )}
        </div>
    );
};
export default EmptyState;