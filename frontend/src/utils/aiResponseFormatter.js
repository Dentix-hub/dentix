/**
 * Format AI API response into chat message structure
 */
export const formatAIResponse = (data) => {
    // Guard: Handle null/undefined response data
    if (!data) {
        return {
            role: 'assistant',
            content: '❌ **خطأ في الاتصال**\n\nلم يتم استلام رد من الخادم. يرجى المحاولة مرة أخرى.',
            type: 'error'
        };
    }
    // 1. Handle Errors
    if (!data.success) {
        const errorCode = data.error || data.error_code;
        let type = 'error';
        let content = data.message || 'حدث خطأ غير متوقع';
        let suggestions = [];

        // Error Mapping
        switch (errorCode) {
            case 'plan_restricted':
            case 'limit_exceeded':
                type = 'warning';
                content = `⛔ **عفواً، الخدمة غير متاحة**\n\n${data.message}`;
                suggestions = ['ترقية الباقة', 'معرفة الاستهلاك'];
                break;

            case 'validation_error':
            case 'missing_parameter':
                type = 'warning';
                content = `⚠️ **بيانات ناقصة**\n\n${data.message}`;
                break;

            case 'not_found':
            case 'patient_not_found':
                type = 'warning';
                content = `🔍 **غير موجود**\n\n${data.message}`;
                suggestions = ['إضافة مريض جديد', 'البحث مرة أخرى'];
                break;

            case 'permission_denied':
                type = 'error';
                content = `🚫 **تصريح مرفوض**\n\nليس لديك صلاحية للقيام بهذا الإجراء.`;
                break;

            case 'confirmation_failed':
                type = 'warning';
                content = `❌ **فشل التأكيد**\n\n${data.message}`;
                break;

            case 'multiple_patients':
                type = 'info';
                content = `🔍 **${data.message}**\n\nيرجى تحديد المريض الصحيح من القائمة أدناه:`;
                if (data.patients) {
                    content += '\n' + data.patients.map(p => `• ${p.name}`).join('\n');
                    suggestions = data.patients.slice(0, 3).map(p => p.name);
                }
                break;

            default:
                // Generic Error
                type = 'error';
                content = `❌ **خطأ في النظام**\n\n${data.message}`;
                if (data.data?.trace) {
                    console.error("AI Trace:", data.data.trace);
                }
        }

        return {
            role: 'assistant',
            content,
            type,
            suggestions: suggestions.length > 0 ? suggestions : undefined,
            originalError: errorCode
        };
    }

    const tool = data.tool;
    const result = data.data || {};

    // Greeting
    if (tool === 'greeting') {
        return {
            role: 'assistant',
            content: data.message,
            type: 'greeting',
            suggestions: result.suggestions
        };
    }

    // Patient File
    if (tool === 'get_patient_file') {
        if (result.patients && result.patients.length > 1) {
            // Multiple matches (Disambiguation)
            const patientList = result.patients.map(p => `• ${p.name} (${p.phone || 'بدون رقم'})`).join('\n');
            return {
                role: 'assistant',
                content: `🔍 **${result.message}**\n\n${patientList}\n\nحدد اسم المريض بالضبط.`,
                type: 'info',
                data: result,
                suggestions: result.patients.slice(0, 3).map(p => `ملف ${p.name}`)
            };
        }
        if (result.patient) {
            const p = result.patient;
            const treatments = result.recent_treatments || [];
            let treatmentText = treatments.length > 0
                ? treatments.slice(0, 3).map(t => `• ${t.procedure} - ${t.cost} جنيه`).join('\n')
                : 'لا توجد علاجات';

            return {
                role: 'assistant',
                content: `📋 **ملف المريض: ${p.name}**\n\n👤 العمر: ${p.age || '-'}\n📞 الهاتف: ${p.phone || '-'}\n📝 التاريخ الطبي: ${p.medical_history || '-'}\n\n**آخر العلاجات:**\n${treatmentText}`,
                type: 'patient',
                data: result,
                suggestions: [`${p.name} عليه كام`, `احجز موعد لـ ${p.name}`]
            };
        }
        // Fallback if success but no patient (shouldn't happen with new error handling, but safe to keep)
        return {
            role: 'assistant',
            content: `❌ ${result.message || 'لم يتم العثور على المريض'}`,
            type: 'warning'
        };
    }

    // Financial Record
    if (tool === 'get_financial_record') {
        return {
            role: 'assistant',
            content: `💰 **${result.message}**\n\n📊 إجمالي التكلفة: ${result.total_cost?.toFixed(2) || 0} جنيه\n✅ المدفوع: ${result.total_paid?.toFixed(2) || 0} جنيه\n💳 المتبقي: ${result.remaining?.toFixed(2) || 0} جنيه\n\n📌 الحالة: ${result.status}`,
            type: result.remaining > 0 ? 'warning' : 'success',
            data: result
        };
    }

    // Appointments
    if (tool === 'get_appointments') {
        if (!result.appointments || result.appointments.length === 0) {
            return {
                role: 'assistant',
                content: `📅 ${result.message}`,
                type: 'info'
            };
        }
        const apptList = result.appointments.map(a =>
            `• ${a.time} - ${a.patient_name} (${a.status})`
        ).join('\n');

        return {
            role: 'assistant',
            content: `📅 **${result.message}**\n\n${apptList}`,
            type: 'appointments',
            data: result
        };
    }

    // Dashboard Stats
    if (tool === 'get_dashboard_stats') {
        return {
            role: 'assistant',
            content: `📊 **${result.message}**\n\n👥 إجمالي المرضى: ${result.total_patients}\n📆 مواعيد اليوم: ${result.today_appointments}\n💵 إيرادات اليوم: ${result.today_revenue?.toFixed(2) || 0} جنيه`,
            type: 'stats',
            data: result
        };
    }

    // Subscription Info
    if (tool === 'get_subscription_info') {
        const sub = result.subscription || {};
        return {
            role: 'assistant',
            content: `📋 **معلومات الاشتراك**\n\n🎫 الخطة: ${sub.plan_name || 'مجاني'}\n💰 السعر: ${sub.plan_price || 0} جنيه\n📌 الحالة: ${sub.status === 'active' ? '✅ نشط' : '❌ غير نشط'}\n📅 تاريخ الانتهاء: ${sub.end_date || 'غير محدد'}`,
            type: sub.is_active ? 'success' : 'warning',
            data: result
        };
    }

    // Clinic Info
    if (tool === 'get_clinic_info') {
        const clinic = result.clinic || {};
        return {
            role: 'assistant',
            content: `🏥 **معلومات العيادة**\n\n📛 الاسم: ${clinic.name || '-'}\n👥 المستخدمين: ${clinic.users_count || 0}\n🧑‍⚕️ المرضى: ${clinic.patients_count || 0}\n📌 حالة الاشتراك: ${clinic.subscription_status || '-'}`,
            type: 'info',
            data: result
        };
    }

    // Users List
    if (tool === 'get_users_list') {
        const usersList = (result.users || []).map(u =>
            `• ${u.full_name || u.username} (${u.role})`
        ).join('\n');
        return {
            role: 'assistant',
            content: `👥 **${result.message}**\n\n${usersList || 'لا يوجد مستخدمين'}`,
            type: 'info',
            data: result
        };
    }

    // Today Payments
    if (tool === 'get_today_payments') {
        const paymentsList = (result.payments || []).slice(0, 10).map(p =>
            `• ${p.patient_name}: ${p.amount} جنيه`
        ).join('\n');
        return {
            role: 'assistant',
            content: `💰 **${result.message}**\n\n📊 عدد المدفوعات: ${result.count || 0}\n\n${paymentsList || 'لا توجد مدفوعات'}`,
            type: 'success',
            data: result
        };
    }

    // Expenses
    if (tool === 'get_expenses') {
        const expensesList = Object.entries(result.by_category || {}).map(([cat, amount]) =>
            `• ${cat}: ${amount.toFixed(2)} جنيه`
        ).join('\n');
        return {
            role: 'assistant',
            content: `💸 **${result.message}**\n\n📊 عدد: ${result.count || 0}\n\n**حسب التصنيف:**\n${expensesList || 'لا توجد مصروفات'}`,
            type: 'warning',
            data: result
        };
    }

    // Lab Orders
    if (tool === 'get_lab_orders') {
        const ordersList = (result.orders || []).slice(0, 10).map(o =>
            `• ${o.patient_name} - ${o.work_type} (${o.status})`
        ).join('\n');
        return {
            role: 'assistant',
            content: `🔬 **${result.message}**\n\n${ordersList || 'لا توجد طلبات'}`,
            type: 'info',
            data: result
        };
    }

    // Recent Treatments
    if (tool === 'get_recent_treatments') {
        const treatmentsList = (result.treatments || []).slice(0, 10).map(t =>
            `• ${t.patient_name} - ${t.procedure}: ${t.cost || 0} جنيه`
        ).join('\n');
        return {
            role: 'assistant',
            content: `🩺 **${result.message}**\n\n${treatmentsList || 'لا توجد علاجات'}`,
            type: 'info',
            data: result
        };
    }

    // Procedures List
    if (tool === 'get_procedures_list') {
        const procList = (result.procedures || []).slice(0, 15).map(p =>
            `• ${p.name}: ${p.price || 0} جنيه`
        ).join('\n');
        return {
            role: 'assistant',
            content: `📋 **${result.message}**\n\n${procList || 'لا توجد إجراءات'}`,
            type: 'info',
            data: result
        };
    }

    // Patients with Balance
    if (tool === 'get_patients_with_balance') {
        const patientsList = (result.patients || []).slice(0, 10).map(p =>
            `• ${p.name}: ${p.balance?.toFixed(2) || 0} جنيه`
        ).join('\n');
        return {
            role: 'assistant',
            content: `💳 **${result.message}**\n\n💰 إجمالي المستحق: ${result.total_outstanding?.toFixed(2) || 0} جنيه\n\n${patientsList || 'لا يوجد مدينين'}`,
            type: result.total_outstanding > 0 ? 'warning' : 'success',
            data: result
        };
    }

    // Create Payment (Action)
    if (tool === 'create_payment') {
        return {
            role: 'assistant',
            content: `${result.message}`,
            type: 'success',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Create Appointment (Action)
    if (tool === 'create_appointment') {
        return {
            role: 'assistant',
            content: `${result.message}`,
            type: 'success',
            data: result,
            suggestions: result.suggestions
        };
    }

    // AI Stats
    if (tool === 'get_ai_stats') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result
        };
    }

    // Smart Scheduling - Available Slots
    if (tool === 'find_available_slots') {
        const slots = (result.available_slots || []).slice(0, 8).join('، ');
        return {
            role: 'assistant',
            content: `📅 **${result.message}**\n\n⏰ المتاح: ${slots || 'لا يوجد'}`,
            type: 'info',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Smart Booking
    if (tool === 'smart_book_appointment') {
        if (result.conflict) {
            return {
                role: 'assistant',
                content: `${result.message}\n\n💡 البدائل المتاحة: ${(result.alternatives || []).join('، ')}`,
                type: 'warning',
                data: result,
                suggestions: result.suggestions
            };
        }
        return {
            role: 'assistant',
            content: result.message,
            type: 'success',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Analytics - Doctor Ranking
    if (tool === 'get_doctor_ranking') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result
        };
    }

    // Analytics - Compare Periods
    if (tool === 'compare_periods') {
        return {
            role: 'assistant',
            content: result.message,
            type: result.change_percent >= 0 ? 'success' : 'warning',
            data: result
        };
    }

    // Analytics - Top Procedures
    if (tool === 'get_top_procedures') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result
        };
    }

    // Analytics - Revenue Trend
    if (tool === 'get_revenue_trend') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result
        };
    }

    // WhatsApp - Reminders
    if (tool === 'send_appointment_reminders') {
        return {
            role: 'assistant',
            content: result.message,
            type: result.requires_whatsapp_api ? 'warning' : 'success',
            data: result
        };
    }

    // WhatsApp - Message
    if (tool === 'send_whatsapp_message') {
        return {
            role: 'assistant',
            content: result.message,
            type: result.requires_whatsapp_api ? 'warning' : 'success',
            data: result
        };
    }

    // Patient Summary
    if (tool === 'summarize_patient') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Medical Scribe - Record Note
    if (tool === 'record_medical_note') {
        return {
            role: 'assistant',
            content: result.message,
            type: result.action === 'note_recorded' ? 'success' : 'warning',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Medical Scribe - Add Treatment
    if (tool === 'add_treatment_voice') {
        return {
            role: 'assistant',
            content: result.message,
            type: result.action === 'treatment_added' ? 'success' : 'warning',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Medical Scribe - Parse Dictation
    if (tool === 'parse_medical_dictation') {
        return {
            role: 'assistant',
            content: result.message,
            type: 'info',
            data: result,
            suggestions: result.suggestions
        };
    }

    // Default
    return {
        role: 'assistant',
        content: data.message || JSON.stringify(result, null, 2),
        type: 'info',
        suggestions: result.suggestions
    };
};
