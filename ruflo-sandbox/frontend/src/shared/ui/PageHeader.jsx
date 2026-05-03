import React from 'react';
import Breadcrumb from './Breadcrumb';

export default function PageHeader({ 
    title, 
    subtitle, 
    icon: Icon, 
    breadcrumbs, 
    actions 
}) {
    return (
        <div className="flex flex-col gap-4 mb-6">
            {breadcrumbs && breadcrumbs.length > 0 && (
                <div className="-mb-2">
                    <Breadcrumb items={breadcrumbs} />
                </div>
            )}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-black text-text-primary tracking-tight flex items-center gap-3">
                        {Icon && <Icon className="text-primary" size={32} />}
                        {title}
                    </h1>
                    {subtitle && (
                        <p className="text-text-secondary mt-1 text-lg font-medium">{subtitle}</p>
                    )}
                </div>
                {actions && (
                    <div className="flex items-center gap-3 w-full md:w-auto">
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
}
