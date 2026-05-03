import { cn } from '@/utils/cn';
import { AlertCircle, AlertTriangle, CheckCircle, Info } from 'lucide-react';

const Alert = ({
    children,
    variant = 'info', // info, warning, error, success
    title,
    className,
    ...props
}) => {
    const variants = {
        info: "bg-blue-50 text-blue-800 border-blue-200",
        warning: "bg-yellow-50 text-yellow-800 border-yellow-200",
        error: "bg-red-50 text-red-800 border-red-200",
        success: "bg-green-50 text-green-800 border-green-200"
    };

    const icons = {
        info: Info,
        warning: AlertTriangle,
        error: AlertCircle,
        success: CheckCircle
    };

    const Icon = icons[variant];

    return (
        <div
            className={cn(
                "p-4 rounded-lg border flex items-start gap-3",
                variants[variant],
                className
            )}
            {...props}
        >
            <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
                {title && <h5 className="font-bold mb-1">{title}</h5>}
                <div className="text-sm opacity-90">{children}</div>
            </div>
        </div>
    );
};

export default Alert;
