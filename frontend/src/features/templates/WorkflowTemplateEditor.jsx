import { useState } from 'react';
import PropTypes from 'prop-types';
import {
    Save,
    Plus,
    Trash2,
    ArrowUp,
    ArrowDown,
    Sliders,
    Layers,
    Eye,
    AlertCircle,
} from 'lucide-react';
import { Button, Badge } from '@/shared/ui';
import { createWorkflowTemplate, updateWorkflowTemplate } from '@/api/workflowTemplates';

const SUPPORTED_PROCEDURES = [
    { code: 'ENDO_RCT', label: 'Endodontic Root Canal Therapy (ENDO_RCT)' },
    { code: 'PROS_CROWN', label: 'Single Crown Restoration (PROS_CROWN)' },
    { code: 'PROS_BRIDGE', label: 'Fixed Partial Denture / Bridge (PROS_BRIDGE)' },
    { code: 'REST_COMPOSITE', label: 'Direct Composite Restoration (REST_COMPOSITE)' },
    { code: 'SURG_EXTRACTION', label: 'Surgical Extraction (SURG_EXTRACTION)' },
    { code: 'PROS_DENTURE', label: 'Removable Denture (PROS_DENTURE)' },
];

const FIELD_TYPES = [
    { type: 'text', label: 'Short Text' },
    { type: 'multiline', label: 'Multiline Text' },
    { type: 'number', label: 'Number' },
    { type: 'choice', label: 'Single Choice' },
    { type: 'boolean', label: 'Yes / No Toggle' },
    { type: 'date', label: 'Date' },
];

export default function WorkflowTemplateEditor({
    template = null, // null for create, object for edit
    onSaveSuccess,
    onCancel,
    t = (k, f) => f || k,
}) {
    const isEditing = Boolean(template && template.id);

    // Form state
    const [templateCode, setTemplateCode] = useState(template?.template_code || 'REST_COMPOSITE');
    const [procedureCode, setProcedureCode] = useState(template?.procedure_code || template?.template_code || 'REST_COMPOSITE');
    const [title, setTitle] = useState(template?.title || '');
    const [description, setDescription] = useState(template?.description || '');
    const [isActive, setIsActive] = useState(template?.is_active ?? true);

    // Active tab in editor: 'steps' | 'fields' | 'preview'
    const [activeTab, setActiveTab] = useState('steps');

    // Steps list
    const [steps, setSteps] = useState(() => {
        const raw = template?.definition?.steps || [];
        if (raw.length > 0) return raw;
        return [
            { step_code: 'assessment', step_order: 1, title: 'Clinical Assessment', description: '', is_required: false, repeatable: false },
            { step_code: 'procedure', step_order: 2, title: 'Main Procedure', description: '', is_required: true, repeatable: false },
            { step_code: 'post_op', step_order: 3, title: 'Post-Operative Verification', description: '', is_required: false, repeatable: false },
        ];
    });

    // Custom fields list
    const [customFields, setCustomFields] = useState(() => {
        return template?.definition?.custom_fields || [];
    });

    const [isSaving, setIsSaving] = useState(false);
    const [validationError, setValidationError] = useState(null);

    // Reorder step helpers
    const moveStep = (index, direction) => {
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= steps.length) return;
        const newSteps = [...steps];
        const temp = newSteps[index];
        newSteps[index] = newSteps[targetIndex];
        newSteps[targetIndex] = temp;
        // Re-assign step_order 1..N
        newSteps.forEach((s, idx) => {
            s.step_order = idx + 1;
        });
        setSteps(newSteps);
    };

    const handleStepChange = (index, field, value) => {
        const newSteps = [...steps];
        newSteps[index] = { ...newSteps[index], [field]: value };
        setSteps(newSteps);
    };

    const addStep = () => {
        const nextOrder = steps.length + 1;
        setSteps([
            ...steps,
            {
                step_code: `step_${nextOrder}`,
                step_order: nextOrder,
                title: `Step ${nextOrder}`,
                description: '',
                is_required: false,
                repeatable: false,
            },
        ]);
    };

    const removeStep = (index) => {
        if (steps.length <= 1) {
            setValidationError('A template must have at least one step.');
            return;
        }
        const newSteps = steps.filter((_, idx) => idx !== index);
        newSteps.forEach((s, idx) => {
            s.step_order = idx + 1;
        });
        setSteps(newSteps);
    };

    // Custom fields helpers
    const addField = () => {
        const count = customFields.length + 1;
        setCustomFields([
            ...customFields,
            {
                field_id: `custom_field_${count}`,
                field_type: 'text',
                label: `Specification ${count}`,
                description: '',
                is_required: false,
                unit: '',
                choices: [],
            },
        ]);
    };

    const handleFieldChange = (index, field, value) => {
        const newFields = [...customFields];
        newFields[index] = { ...newFields[index], [field]: value };
        setCustomFields(newFields);
    };

    const handleChoicesChange = (index, textVal) => {
        const items = textVal
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean);
        handleFieldChange(index, 'choices', items);
    };

    const removeField = (index) => {
        setCustomFields(customFields.filter((_, idx) => idx !== index));
    };

    // Form validation before submit
    const validate = () => {
        if (!title.trim()) {
            return 'Template title is required.';
        }
        if (!templateCode.trim()) {
            return 'Template code is required.';
        }
        if (steps.length === 0) {
            return 'At least one step is required.';
        }
        const seenCodes = new Set();
        for (const s of steps) {
            if (!s.step_code.trim()) return 'All steps must have a step code.';
            if (!s.title.trim()) return 'All steps must have a title.';
            if (seenCodes.has(s.step_code.trim().toLowerCase())) {
                return `Duplicate step code: ${s.step_code}`;
            }
            seenCodes.add(s.step_code.trim().toLowerCase());
        }
        const seenFieldIds = new Set();
        for (const f of customFields) {
            if (!f.field_id.trim()) return 'All custom fields must have an identifier.';
            if (!f.label.trim()) return 'All custom fields must have a label.';
            if (seenFieldIds.has(f.field_id.trim().toLowerCase())) {
                return `Duplicate custom field identifier: ${f.field_id}`;
            }
            seenFieldIds.add(f.field_id.trim().toLowerCase());
            if (f.field_type === 'choice' && (!f.choices || f.choices.length === 0)) {
                return `Choice field '${f.label}' must have at least one option.`;
            }
        }
        return null;
    };

    const handleSave = async () => {
        const err = validate();
        if (err) {
            setValidationError(err);
            return;
        }
        setValidationError(null);
        setIsSaving(true);

        const payload = {
            template_code: templateCode.trim().toUpperCase(),
            procedure_code: procedureCode.trim().toUpperCase(),
            title: title.trim(),
            description: description.trim() || null,
            is_active: isActive,
            definition: {
                steps: steps.map((s, idx) => ({
                    step_code: s.step_code.trim().toLowerCase(),
                    step_order: idx + 1,
                    title: s.title.trim(),
                    description: s.description?.trim() || null,
                    is_required: Boolean(s.is_required),
                    repeatable: Boolean(s.repeatable),
                })),
                custom_fields: customFields.map((f) => ({
                    field_id: f.field_id.trim().toLowerCase(),
                    field_type: f.field_type,
                    label: f.label.trim(),
                    description: f.description?.trim() || null,
                    is_required: Boolean(f.is_required),
                    unit: f.unit?.trim() || null,
                    choices: f.choices || [],
                })),
            },
        };

        try {
            if (isEditing) {
                // Updating creates a new version
                await updateWorkflowTemplate(template.id || template.template_code, payload);
            } else {
                await createWorkflowTemplate(payload);
            }
            if (onSaveSuccess) onSaveSuccess();
        } catch (error) {
            setValidationError(error?.response?.data?.detail || error.message || 'Failed to save template');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div data-testid="workflow-template-editor" className="space-y-6">
            {/* Header with Title & Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
                <div>
                    <h3 className="text-lg font-bold text-text-primary">
                        {isEditing
                            ? `${t('templates.edit_title', 'Edit Clinic Template')} (${template.template_code} v${template.version})`
                            : t('templates.create_title', 'Create Clinic Workflow Template')}
                    </h3>
                    <p className="text-xs text-text-secondary mt-0.5">
                        {t('templates.editor_subtitle', 'Configure clinical steps and chairside custom fields without modifying past visit history.')}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={onCancel} disabled={isSaving}>
                        {t('common.cancel', 'Cancel')}
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={handleSave}
                        disabled={isSaving}
                        data-testid="btn-save-template"
                        className="gap-1.5 font-bold"
                    >
                        <Save className="h-4 w-4" />
                        <span>{isSaving ? t('common.saving', 'Saving...') : t('common.save_version', 'Save Version')}</span>
                    </Button>
                </div>
            </div>

            {validationError && (
                <div
                    data-testid="template-validation-error"
                    className="flex items-center gap-2 rounded-xl bg-danger/10 border border-danger/20 p-3 text-xs font-bold text-danger"
                >
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{validationError}</span>
                </div>
            )}

            {/* Template Metadata Header Form */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 rounded-2xl border border-border bg-surface-elevated p-4">
                <div className="space-y-1">
                    <label className="text-xs font-bold text-text-primary">
                        {t('templates.procedure_association', 'Procedure Family')}
                    </label>
                    <select
                        value={procedureCode}
                        onChange={(e) => {
                            setProcedureCode(e.target.value);
                            if (!isEditing) setTemplateCode(e.target.value);
                        }}
                        disabled={isEditing}
                        data-testid="select-procedure-code"
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary disabled:opacity-60"
                    >
                        {SUPPORTED_PROCEDURES.map((p) => (
                            <option key={p.code} value={p.code}>
                                {p.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="space-y-1">
                    <label className="text-xs font-bold text-text-primary">
                        {t('templates.template_code', 'Template Identifier (Code)')}
                    </label>
                    <input
                        type="text"
                        value={templateCode}
                        onChange={(e) => setTemplateCode(e.target.value.toUpperCase())}
                        disabled={isEditing}
                        data-testid="input-template-code"
                        placeholder="e.g. REST_COMPOSITE"
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary disabled:opacity-60"
                    />
                </div>

                <div className="space-y-1 sm:col-span-2">
                    <label className="text-xs font-bold text-text-primary">
                        {t('templates.display_title', 'Template Display Title')} *
                    </label>
                    <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        data-testid="input-template-title"
                        placeholder="e.g. Composite Restoration Documentation Workflow"
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                    />
                </div>

                <div className="space-y-1 sm:col-span-3">
                    <label className="text-xs font-bold text-text-primary">
                        {t('templates.description', 'Workflow Description / Notes')}
                    </label>
                    <input
                        type="text"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        data-testid="input-template-description"
                        placeholder="Brief overview of clinical scope covered by this template"
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                    />
                </div>

                <div className="flex items-center gap-2 pt-5">
                    <input
                        type="checkbox"
                        id="tpl_is_active"
                        checked={isActive}
                        onChange={(e) => setIsActive(e.target.checked)}
                        data-testid="input-template-active"
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <label htmlFor="tpl_is_active" className="text-xs font-bold text-text-primary">
                        {t('templates.active_for_new_visits', 'Active for new visits')}
                    </label>
                </div>
            </div>

            {/* Navigation Tabs: Steps | Custom Fields | Live Preview */}
            <div className="flex items-center gap-2 border-b border-border">
                <button
                    type="button"
                    onClick={() => setActiveTab('steps')}
                    data-testid="tab-steps"
                    className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition-colors ${
                        activeTab === 'steps'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-text-secondary hover:text-text-primary'
                    }`}
                >
                    <Layers className="h-4 w-4" />
                    <span>{t('templates.workflow_steps_tab', 'Workflow Steps')} ({steps.length})</span>
                </button>

                <button
                    type="button"
                    onClick={() => setActiveTab('fields')}
                    data-testid="tab-custom-fields"
                    className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition-colors ${
                        activeTab === 'fields'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-text-secondary hover:text-text-primary'
                    }`}
                >
                    <Sliders className="h-4 w-4" />
                    <span>{t('templates.custom_fields_tab', 'Configurable Fields')} ({customFields.length})</span>
                </button>

                <button
                    type="button"
                    onClick={() => setActiveTab('preview')}
                    data-testid="tab-preview"
                    className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition-colors ${
                        activeTab === 'preview'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-text-secondary hover:text-text-primary'
                    }`}
                >
                    <Eye className="h-4 w-4" />
                    <span>{t('templates.preview_tab', 'Interactive Preview')}</span>
                </button>
            </div>

            {/* Tab 1: Workflow Steps */}
            {activeTab === 'steps' && (
                <div data-testid="section-steps" className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-text-secondary">
                            {t('templates.steps_reorder_guidance', 'Define sequential steps. Use arrows to reorder.')}
                        </span>
                        <Button
                            variant="outline"
                            size="xs"
                            onClick={addStep}
                            data-testid="btn-add-step"
                            className="gap-1 font-bold text-xs"
                        >
                            <Plus className="h-3.5 w-3.5" />
                            <span>{t('templates.add_step_btn', 'Add Step')}</span>
                        </Button>
                    </div>

                    <div className="space-y-2.5">
                        {steps.map((step, idx) => (
                            <div
                                key={idx}
                                data-testid={`step-item-${idx}`}
                                className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface-elevated p-3 shadow-xs"
                            >
                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-surface font-black text-xs text-text-secondary border border-border">
                                    {idx + 1}
                                </span>

                                <div className="w-32">
                                    <input
                                        type="text"
                                        value={step.step_code}
                                        onChange={(e) => handleStepChange(idx, 'step_code', e.target.value.toLowerCase())}
                                        data-testid={`step-code-${idx}`}
                                        placeholder="code_slug"
                                        className="w-full rounded-lg border border-border bg-surface px-2 py-1 text-xs font-mono text-text-primary"
                                    />
                                </div>

                                <div className="flex-1 min-w-[180px]">
                                    <input
                                        type="text"
                                        value={step.title}
                                        onChange={(e) => handleStepChange(idx, 'title', e.target.value)}
                                        data-testid={`step-title-${idx}`}
                                        placeholder="Step Title"
                                        className="w-full rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-bold text-text-primary"
                                    />
                                </div>

                                <div className="flex items-center gap-2">
                                    <label className="flex items-center gap-1 text-2xs text-text-secondary cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={Boolean(step.is_required)}
                                            onChange={(e) => handleStepChange(idx, 'is_required', e.target.checked)}
                                            className="rounded border-border text-primary"
                                        />
                                        <span>Required</span>
                                    </label>

                                    <label className="flex items-center gap-1 text-2xs text-text-secondary cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={Boolean(step.repeatable)}
                                            onChange={(e) => handleStepChange(idx, 'repeatable', e.target.checked)}
                                            className="rounded border-border text-primary"
                                        />
                                        <span>Repeatable</span>
                                    </label>
                                </div>

                                <div className="flex items-center gap-1 ms-auto">
                                    <button
                                        type="button"
                                        onClick={() => moveStep(idx, 'up')}
                                        disabled={idx === 0}
                                        data-testid={`btn-move-up-${idx}`}
                                        className="rounded-lg p-1 text-text-secondary hover:text-text-primary disabled:opacity-30"
                                        title="Move step up"
                                    >
                                        <ArrowUp className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => moveStep(idx, 'down')}
                                        disabled={idx === steps.length - 1}
                                        data-testid={`btn-move-down-${idx}`}
                                        className="rounded-lg p-1 text-text-secondary hover:text-text-primary disabled:opacity-30"
                                        title="Move step down"
                                    >
                                        <ArrowDown className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => removeStep(idx)}
                                        data-testid={`btn-remove-step-${idx}`}
                                        className="rounded-lg p-1 text-text-secondary hover:text-danger"
                                        title="Delete step"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Tab 2: Configurable Custom Fields */}
            {activeTab === 'fields' && (
                <div data-testid="section-custom-fields" className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-text-secondary">
                            {t('templates.fields_guidance', 'Add chairside inputs (e.g. shade, materials, measurements).')}
                        </span>
                        <Button
                            variant="outline"
                            size="xs"
                            onClick={addField}
                            data-testid="btn-add-field"
                            className="gap-1 font-bold text-xs"
                        >
                            <Plus className="h-3.5 w-3.5" />
                            <span>{t('templates.add_field_btn', 'Add Field')}</span>
                        </Button>
                    </div>

                    {customFields.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-border p-8 text-center text-xs text-text-secondary">
                            {t('templates.no_custom_fields', 'No custom fields defined for this template yet. Click "Add Field" to create one.')}
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {customFields.map((field, idx) => (
                                <div
                                    key={idx}
                                    data-testid={`custom-field-item-${idx}`}
                                    className="rounded-2xl border border-border bg-surface-elevated p-4 shadow-xs space-y-3"
                                >
                                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-text-secondary uppercase">
                                                Identifier (slug)
                                            </label>
                                            <input
                                                type="text"
                                                value={field.field_id}
                                                onChange={(e) => handleFieldChange(idx, 'field_id', e.target.value.toLowerCase())}
                                                data-testid={`field-id-${idx}`}
                                                placeholder="e.g. tooth_shade"
                                                className="w-full rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-mono text-text-primary"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-text-secondary uppercase">
                                                Field Type
                                            </label>
                                            <select
                                                value={field.field_type}
                                                onChange={(e) => handleFieldChange(idx, 'field_type', e.target.value)}
                                                data-testid={`field-type-${idx}`}
                                                className="w-full rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                                            >
                                                {FIELD_TYPES.map((ft) => (
                                                    <option key={ft.type} value={ft.type}>
                                                        {ft.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        <div className="space-y-1 sm:col-span-2">
                                            <label className="text-2xs font-bold text-text-secondary uppercase">
                                                Display Label
                                            </label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="text"
                                                    value={field.label}
                                                    onChange={(e) => handleFieldChange(idx, 'label', e.target.value)}
                                                    data-testid={`field-label-${idx}`}
                                                    placeholder="e.g. Tooth Shade"
                                                    className="w-full rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-bold text-text-primary"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => removeField(idx)}
                                                    data-testid={`btn-remove-field-${idx}`}
                                                    className="rounded-lg p-1.5 text-text-secondary hover:text-danger"
                                                    title="Remove field"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Additional Settings row */}
                                    <div className="flex flex-wrap items-center gap-4 pt-1">
                                        {field.field_type === 'number' && (
                                            <div className="flex items-center gap-1.5">
                                                <span className="text-2xs font-bold text-text-secondary">Unit:</span>
                                                <input
                                                    type="text"
                                                    value={field.unit || ''}
                                                    onChange={(e) => handleFieldChange(idx, 'unit', e.target.value)}
                                                    placeholder="e.g. mm, Ncm, min"
                                                    className="w-24 rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                                                />
                                            </div>
                                        )}

                                        {field.field_type === 'choice' && (
                                            <div className="flex-1 min-w-[240px]">
                                                <span className="text-2xs font-bold text-text-secondary">
                                                    Choices (comma-separated):
                                                </span>
                                                <input
                                                    type="text"
                                                    value={(field.choices || []).join(', ')}
                                                    onChange={(e) => handleChoicesChange(idx, e.target.value)}
                                                    placeholder="Option 1, Option 2, Option 3"
                                                    className="w-full rounded-lg border border-border bg-surface px-2.5 py-1 text-xs text-text-primary"
                                                />
                                            </div>
                                        )}

                                        <label className="flex items-center gap-1.5 text-xs font-semibold text-text-primary cursor-pointer ms-auto">
                                            <input
                                                type="checkbox"
                                                checked={Boolean(field.is_required)}
                                                onChange={(e) => handleFieldChange(idx, 'is_required', e.target.checked)}
                                                className="rounded border-border text-primary"
                                            />
                                            <span>Required at Visit Finalization</span>
                                        </label>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Tab 3: Interactive Preview */}
            {activeTab === 'preview' && (
                <div
                    data-testid="section-preview"
                    className="rounded-2xl border border-primary/20 bg-surface-elevated p-6 shadow-xs space-y-6"
                >
                    <div className="border-b border-border pb-3">
                        <Badge variant="primary" size="xs" className="mb-1 font-bold">
                            Live Chairside Preview
                        </Badge>
                        <h4 className="text-base font-bold text-text-primary">{title || 'Template Title'}</h4>
                        {description && <p className="text-xs text-text-secondary">{description}</p>}
                    </div>

                    {/* Steps Preview */}
                    <div className="space-y-2">
                        <h5 className="text-xs font-bold text-text-secondary uppercase">
                            Steps Simulation ({steps.length})
                        </h5>
                        <div className="space-y-1.5">
                            {steps.map((s, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center gap-2 rounded-xl border border-border bg-surface p-2.5 text-xs"
                                >
                                    <span className="flex h-5 w-5 items-center justify-center rounded-md bg-surface-elevated text-xs font-bold">
                                        {idx + 1}
                                    </span>
                                    <span className="font-bold text-text-primary">{s.title}</span>
                                    {s.is_required && <Badge variant="warning" size="xs">Required</Badge>}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Custom Fields Preview */}
                    {customFields.length > 0 && (
                        <div className="space-y-2 pt-2">
                            <h5 className="text-xs font-bold text-text-secondary uppercase">
                                Custom Fields Simulation ({customFields.length})
                            </h5>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                                {customFields.map((f, idx) => (
                                    <div key={idx} className="rounded-xl border border-border bg-surface p-3 text-xs space-y-1">
                                        <div className="font-bold text-text-primary">
                                            {f.label} {f.unit && `(${f.unit})`}
                                        </div>
                                        <div className="text-2xs text-text-secondary">Type: {f.field_type}</div>
                                        {f.field_type === 'choice' && (
                                            <div className="flex flex-wrap gap-1 pt-1">
                                                {(f.choices || []).map((c, i) => (
                                                    <span key={i} className="rounded-md bg-surface-elevated px-2 py-0.5 text-2xs border border-border">
                                                        {c}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

WorkflowTemplateEditor.propTypes = {
    template: PropTypes.object,
    onSaveSuccess: PropTypes.func.isRequired,
    onCancel: PropTypes.func.isRequired,
    t: PropTypes.func,
};
