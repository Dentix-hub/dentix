import { Upload, RefreshCw, Edit2, Trash2, FileText, File as FileIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { API_URL } from '@/api';

const PatientFiles = ({
    attachments,
    handleFileUpload,
    handleDeleteAttachment,
    loading,
    reloadAttachments
}) => {
    const { t } = useTranslation();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                <h3 className="font-bold text-slate-700 flex items-center gap-2">
                    <FileIcon size={20} className="text-slate-400" />
                    {t('patientDetails.files.title')}
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={reloadAttachments}
                        className="p-2 text-slate-500 hover:text-primary hover:bg-slate-50 rounded-lg transition-colors"
                        title={t('patientDetails.files.refresh_tooltip')}
                    >
                        <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <label className="flex items-center gap-2 px-4 py-2 bg-primary text-white font-bold rounded-lg hover:bg-sky-600 cursor-pointer transition-colors shadow-lg shadow-primary/20">
                        <Upload size={18} />
                        {t('patientDetails.files.upload')}
                        <input type="file" className="hidden" onChange={handleFileUpload} accept="image/*,.pdf" />
                    </label>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {(Array.isArray(attachments) ? attachments : []).map(file => (
                    <div key={file.id} className="group relative aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
                        {file.file_type.includes('image') ? (
                            <img
                                src={(() => {
                                    if (!file.file_path) return '';
                                    if (file.file_path.startsWith('http')) return file.file_path;
                                    if (file.file_path.includes('http')) return file.file_path.substring(file.file_path.indexOf('http'));
                                    return `${API_URL || ''}/${file.file_path}`.replace('//', '/');
                                })()}
                                alt={file.filename}
                                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                onClick={() => {
                                    const url = file.file_path.startsWith('http') ? file.file_path :
                                        (file.file_path.includes('http') ? file.file_path.substring(file.file_path.indexOf('http')) :
                                            `${API_URL || ''}/${file.file_path}`.replace('//', '/'));
                                    window.open(url, '_blank');
                                }}
                            />
                        ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 p-4 text-center">
                                <FileText size={40} className="mb-2" />
                                <span className="text-xs truncate w-full">{file.filename}</span>
                            </div>
                        )}

                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <button
                                onClick={() => window.open(file.file_path.startsWith('http') ? file.file_path : `${API_URL || ''}/${file.file_path}`.replace('//', '/'), '_blank')}
                                className="p-2 bg-white rounded-full text-slate-700 hover:text-primary hover:scale-110 transition-all"
                            >
                                <Edit2 size={16} />
                            </button>
                            <button
                                onClick={() => handleDeleteAttachment(file.id)}
                                className="p-2 bg-white rounded-full text-slate-700 hover:text-red-500 hover:scale-110 transition-all"
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                        <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/60 to-transparent text-white text-xs truncate">
                            {new Date(file.created_at).toLocaleDateString()}
                        </div>
                    </div>
                ))}
                {attachments.length === 0 && (
                    <div className="col-span-full py-12 text-center text-slate-400 bg-slate-50 border border-dashed border-slate-200 rounded-xl">
                        <Upload size={48} className="mx-auto mb-3 opacity-20" />
                        <p>{t('patientDetails.files.empty')}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PatientFiles;
