import { isValidElement } from 'react';
import { Loader2 } from 'lucide-react';

const Button = ({
    children,
    variant = 'primary', // primary, secondary, outline, ghost, danger
    size = 'md', // sm, md, lg
    isLoading = false,
    disabled = false,
    icon: Icon,
    className = '',
    onClick,
    type = 'button',
    ...props
}) => {
    const baseStyles = "inline-flex items-center justify-center rounded-xl font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]";

    const variants = {
        primary: "bg-primary text-white hover:bg-primary-600 shadow-lg shadow-primary/20 hover:shadow-primary/30",
        secondary: "bg-surface-hover text-text-primary hover:bg-slate-200 dark:hover:bg-slate-700 border border-border",
        outline: "border-2 border-primary text-primary hover:bg-primary/5",
        ghost: "text-text-secondary hover:text-primary hover:bg-primary/5",
        danger: "bg-red-500 text-white hover:bg-red-600 shadow-lg shadow-red-500/20"
    };

    const sizes = {
        sm: "px-3 py-1.5 text-xs",
        md: "px-5 py-2.5 text-sm",
        lg: "px-6 py-3.5 text-base"
    };

    return (
        <button
            type={type}
            className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
            onClick={onClick}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : Icon ? (
                isValidElement(Icon) ? (
                    <span className="mr-2">{Icon}</span>
                ) : (
                    <Icon className={`mr-2 ${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} />
                )
            ) : null}

            {children}
        </button>
    );
};

export default Button;
