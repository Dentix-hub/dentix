import { cn } from '@/utils/cn';

const IconButton = ({
    icon,
    onClick,
    variant = 'ghost', // ghost, outline, primary, danger
    size = 'md', // sm, md, lg
    className,
    disabled = false,
    type = 'button',
    ...props
}) => {
    const baseStyles = "inline-flex items-center justify-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-primary text-white hover:bg-primary-600 shadow-md",
        outline: "border border-gray-200 hover:bg-gray-50 text-gray-700",
        ghost: "text-gray-500 hover:bg-gray-100 hover:text-gray-900",
        danger: "bg-red-50 text-red-600 hover:bg-red-100"
    };

    const sizes = {
        sm: "p-1.5",
        md: "p-2",
        lg: "p-3"
    };

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={cn(baseStyles, variants[variant], sizes[size], className)}
            {...props}
        >
            {icon}
        </button>
    );
};

export default IconButton;