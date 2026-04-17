import React, { memo } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/shared/ui';

export default memo(function PatientFilters({ search, onSearchChange }) {
    return (
        <div className="sticky top-0 z-10 bg-slate-50/80 backdrop-blur-sm py-3">
            <Input
                type="text"
                placeholder="Search by name or phone..."
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                icon={<Search className="w-4 h-4 text-slate-400" />}
                containerClassName="max-w-md"
                dir="auto"
            />
        </div>
    );
});
