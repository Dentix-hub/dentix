// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'financial_transaction_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$FinancialTransactionModelImpl _$$FinancialTransactionModelImplFromJson(
        Map<String, dynamic> json) =>
    _$FinancialTransactionModelImpl(
      id: (json['id'] as num).toInt(),
      type: json['type'] as String,
      amount: (json['amount'] as num).toDouble(),
      date: json['date'] as String,
      description: json['description'] as String?,
      patientId: (json['patient_id'] as num?)?.toInt(),
      patientName: json['patient_name'] as String?,
      appointmentId: (json['appointment_id'] as num?)?.toInt(),
      treatmentId: (json['treatment_id'] as num?)?.toInt(),
      category: json['category'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$FinancialTransactionModelImplToJson(
        _$FinancialTransactionModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'amount': instance.amount,
      'date': instance.date,
      'description': instance.description,
      'patient_id': instance.patientId,
      'patient_name': instance.patientName,
      'appointment_id': instance.appointmentId,
      'treatment_id': instance.treatmentId,
      'category': instance.category,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$FinancialOverviewResponseModelImpl
    _$$FinancialOverviewResponseModelImplFromJson(Map<String, dynamic> json) =>
        _$FinancialOverviewResponseModelImpl(
          items: (json['items'] as List<dynamic>)
              .map((e) =>
                  FinancialTransactionModel.fromJson(e as Map<String, dynamic>))
              .toList(),
          totalRevenue: (json['total_revenue'] as num).toInt(),
          totalExpenses: (json['total_expenses'] as num).toInt(),
          netIncome: (json['net_income'] as num).toDouble(),
          currentPage: (json['current_page'] as num).toInt(),
          totalPages: (json['total_pages'] as num).toInt(),
          totalItems: (json['total_items'] as num).toInt(),
        );

Map<String, dynamic> _$$FinancialOverviewResponseModelImplToJson(
        _$FinancialOverviewResponseModelImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total_revenue': instance.totalRevenue,
      'total_expenses': instance.totalExpenses,
      'net_income': instance.netIncome,
      'current_page': instance.currentPage,
      'total_pages': instance.totalPages,
      'total_items': instance.totalItems,
    };

_$RecordPaymentRequestModelImpl _$$RecordPaymentRequestModelImplFromJson(
        Map<String, dynamic> json) =>
    _$RecordPaymentRequestModelImpl(
      patientId: (json['patient_id'] as num).toInt(),
      amount: (json['amount'] as num).toDouble(),
      date: json['date'] as String,
      description: json['description'] as String?,
      appointmentId: (json['appointment_id'] as num?)?.toInt(),
      treatmentId: (json['treatment_id'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$RecordPaymentRequestModelImplToJson(
        _$RecordPaymentRequestModelImpl instance) =>
    <String, dynamic>{
      'patient_id': instance.patientId,
      'amount': instance.amount,
      'date': instance.date,
      'description': instance.description,
      'appointment_id': instance.appointmentId,
      'treatment_id': instance.treatmentId,
    };
