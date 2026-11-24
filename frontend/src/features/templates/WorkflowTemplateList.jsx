import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
    Plus,
    Layers,
    CheckCircle2,
    XCircle,
    Edit3,
    Search,
    RefreshCw,
} from 'lucide-react';
import { Button, Badge, EmptyState } from '@/shared/ui';
import WorkflowTemplateEditor from './WorkflowTemplateEditor';
import { getWorkflowTemplates, updateWorkflowTemplateStatus } from '@/api/workflowTemplates';

export default function WorkflowTemplateList({ t: tProp }) {
    const { t: i18nT } = useTranslation();
    const t = tProp || i18nT;
    const queryClient = useQueryClient();
    const [editingTemplate, setEditingTemplate] = useState(null);
    const [isCreating, setIsCreating] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const {
        data: templates = [],
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ['workflow-templates'],
        queryFn: async () => {
            const res = await getWorkflowTemplates({ include_inactive: true });
            return Array.isArray(res?.data) ? res.data : (res?.data?.data || []);
        },
    });

    const statusMutation = useMutation({
        mutationFn: async ({ templateId, isActive }) => {
            await updateWorkflowTemplateStatus(templateId, { is_active: isActive });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workflow-templates'] });
        },
    });

    const filteredTemplates = templates.filter((tpl) => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
            tpl.template_code?.toLowerCase().includes(q) ||
            tpl.title?.toLowerCase().includes(q) ||
            tpl.procedure_code?.toLowerCase().includes(q)
        );
    });

    if (editingTemplate || isCreating) {
        return (
            <WorkflowTemplateEditor
                template={editingTemplate}
                onSaveSuccess={() => {
                    setEditingTemplate(null);
                    setIsCreating(false);
                    queryClient.invalidateQueries({ queryKey: ['workflow-templates'] });
                }}
                onCancel={() => {
                    setEditingTemplate(null);
                    setIsCreating(false);
                }}
                t={t}
            />
        );
    }

    return (
        <div data-testid="workflow-template-list-page" className="space-y-6">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
                <div>
                    <h2 className="text-xl font-bold text-text-primary">
                        {t('templates.page_title', 'Clinical Workflow Templates & Custom Fields')}
                    </h2>
                    <p className="text-xs text-text-secondary mt-0.5">
                        {t('templates.page_subtitle', 'Manage procedural blueprints, ordered stages, and chairside documentation fields for your clinic.')}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setIsCreating(true)}
                        data-testid="btn-create-template"
                        className="gap-1.5 font-bold"
                    >
                        <Plus className="h-4 w-4" />
                        <span>{t('templates.new_template_btn', 'New Template')}</span>
                    </Button>
                </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="relative flex-1 min-w-[240px] max-w-md">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-secondary" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder={t('templates.search_placeholder', 'Search templates by code, procedure or title...')}
                        className="w-full rounded-xl border border-border bg-surface pl-9 pr-3 py-2 text-xs text-text-primary"
                    />
                </div>
                <Button variant="ghost" size="xs" onClick={() => refetch()} className="gap-1 text-xs">
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>{t('common.refresh', 'Refresh')}</span>
                </Button>
            </div>

            {/* Templates Table / Grid */}
            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="h-20 w-full animate-pulse rounded-2xl bg-surface-elevated" />
                    ))}
                </div>
            ) : error ? (
                <div className="rounded-2xl border border-danger/20 bg-danger/10 p-6 text-center text-xs font-bold text-danger">
                    {error.message || t('templates.load_error', 'Failed to load templates')}
                </div>
            ) : filteredTemplates.length === 0 ? (
                <EmptyState
                    title={t('templates.empty_title', 'No Workflow Templates Found')}
                    description={t('templates.empty_desc', 'Create a clinic-owned template or adjust your search filter.')}
                    icon={Layers}
                    action={
                        <Button variant="primary" onClick={() => setIsCreating(true)}>
                            {t('templates.create_first', 'Create Template')}
                        </Button>
                    }
                />
            ) : (
                <div className="overflow-hidden rounded-2xl border border-border bg-surface-elevated shadow-xs">
                    <table className="w-full border-collapse text-start text-xs">
                        <thead>
                            <tr className="border-b border-border bg-surface text-2xs font-bold text-text-secondary uppercase">
                                <th className="px-4 py-3">{t('templates.col_template_procedure', 'Template / Procedure')}</th>
                                <th className="px-4 py-3">{t('templates.col_version', 'Version')}</th>
                                <th className="px-4 py-3">{t('templates.col_steps', 'Steps')}</th>
                                <th className="px-4 py-3">{t('templates.col_custom_fields', 'Custom Fields')}</th>
                                <th className="px-4 py-3">{t('templates.col_type', 'Type')}</th>
                                <th className="px-4 py-3">{t('templates.col_status', 'Status')}</th>
                                <th className="px-4 py-3 text-end">{t('templates.col_actions', 'Actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {filteredTemplates.map((tpl) => {
                                const stepCount = tpl.definition?.steps?.length || 0;
                                const fieldCount = tpl.definition?.custom_fields?.length || 0;

                                return (
                                    <tr
                                        key={tpl.id || tpl.template_code}
                                        data-testid={`template-row-${tpl.template_code}`}
                                        className="hover:bg-surface/50 transition-colors"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="font-bold text-text-primary">{tpl.title}</div>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="font-mono text-2xs font-bold text-text-secondary">
                                                    {tpl.template_code}
                                                </span>
                                                {tpl.procedure_code && (
                                                    <span className="text-2xs text-text-secondary">
                                                        ({tpl.procedure_code})
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 font-semibold text-text-secondary">
                                            v{tpl.version}
                                        </td>
                                        <td className="px-4 py-3 font-semibold text-text-primary">
                                            <Badge variant="neutral" size="xs">
                                                {stepCount} {stepCount === 1 ? t('templates.step_one', 'step') : t('templates.step_other', 'steps')}
                                            </Badge>
                                        </td>
                                        <td className="px-4 py-3 font-semibold text-text-primary">
                                            {fieldCount > 0 ? (
                                                <Badge variant="primary" size="xs">
                                                    {fieldCount} {fieldCount === 1 ? t('templates.field_one', 'field') : t('templates.field_other', 'fields')}
                                                </Badge>
                                            ) : (
                                                <span className="text-text-secondary text-2xs">{t('templates.none', 'None')}</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            {tpl.is_customized ? (
                                                <Badge variant="success" size="xs" className="font-bold">
                                                    {t('templates.type_clinic_custom', 'Clinic Custom')}
                                                </Badge>
                                            ) : (
                                                <Badge variant="neutral" size="xs">
                                                    {t('templates.type_system_default', 'System Default')}
                                                </Badge>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <button
                                                type="button"
                                                disabled={statusMutation.isPending || !tpl.id}
                                                onClick={() => tpl.id && statusMutation.mutate({ templateId: tpl.id, isActive: !tpl.is_active })}
                                                className="inline-flex items-center gap-1 cursor-pointer hover:opacity-80 disabled:cursor-default"
                                                title={
                                                    tpl.id
                                                        ? (tpl.is_active
                                                            ? t('templates.tooltip_deactivate', 'Click to deactivate')
                                                            : t('templates.tooltip_activate', 'Click to activate'))
                                                        : t('templates.tooltip_default', 'Default template')
                                                }
                                            >
                                                {tpl.is_active ? (
                                                    <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-bold">
                                                        <CheckCircle2 className="h-3.5 w-3.5" />
                                                        <span>{t('templates.status_active', 'Active')}</span>
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1 text-text-secondary font-bold">
                                                        <XCircle className="h-3.5 w-3.5" />
                                                        <span>{t('templates.status_inactive', 'Inactive')}</span>
                                                    </span>
                                                )}
                                            </button>
                                        </td>
                                        <td className="px-4 py-3 text-end">
                                            <Button
                                                variant="outline"
                                                size="xs"
                                                onClick={() => setEditingTemplate(tpl)}
                                                data-testid={`btn-edit-${tpl.template_code}`}
                                                className="gap-1 font-bold text-xs"
                                            >
                                                <Edit3 className="h-3 w-3" />
                                                <span>{tpl.is_customized ? t('templates.edit_version', 'Edit Version') : t('templates.customize', 'Customize')}</span>
                                            </Button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
