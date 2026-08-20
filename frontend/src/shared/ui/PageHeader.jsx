import Breadcrumb from './Breadcrumb';

export default function PageHeader({
    title,
    subtitle,
    icon: Icon,
    breadcrumbs,
    actions
}) {
    return (
        <div className="mb-5 flex min-w-0 flex-col gap-4 sm:mb-6">
            {breadcrumbs && breadcrumbs.length > 0 && (
                <div className="-mb-2 min-w-0 overflow-hidden">
                    <Breadcrumb items={breadcrumbs} />
                </div>
            )}
            <div className="flex min-w-0 flex-col items-stretch justify-between gap-4 md:flex-row md:items-center">
                <div className="min-w-0">
                    <h1 className="flex min-w-0 items-start gap-2.5 text-2xl font-extrabold tracking-tight text-text-primary sm:items-center sm:gap-3 sm:text-3xl">
                        {Icon && <Icon className="mt-0.5 shrink-0 text-primary sm:mt-0" size={30} aria-hidden="true" />}
                        <span className="min-w-0 break-words">{title}</span>
                    </h1>
                    {subtitle && (
                        <p className="mt-1 min-w-0 break-words text-sm font-medium text-text-secondary sm:text-base md:text-lg">
                            {subtitle}
                        </p>
                    )}
                </div>
                {actions && (
                    <div className="flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3 md:w-auto md:justify-end [&>*]:w-full sm:[&>*]:w-auto">
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
}
