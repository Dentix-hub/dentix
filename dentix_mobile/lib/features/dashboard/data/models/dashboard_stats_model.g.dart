// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'dashboard_stats_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$DashboardStatsModelImpl _$$DashboardStatsModelImplFromJson(
        Map<String, dynamic> json) =>
    _$DashboardStatsModelImpl(
      totalPatients: (json['total_patients'] as num).toInt(),
      todayAppointments: (json['total_appointments_today'] as num).toInt(),
      todayRevenue: (json['today_revenue'] as num).toDouble(),
      totalRevenue: (json['total_revenue'] as num?)?.toDouble(),
      pendingAppointments: (json['pending_appointments'] as num?)?.toInt(),
      completedAppointments: (json['completed_appointments'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$DashboardStatsModelImplToJson(
        _$DashboardStatsModelImpl instance) =>
    <String, dynamic>{
      'total_patients': instance.totalPatients,
      'today_appointments': instance.todayAppointments,
      'today_revenue': instance.todayRevenue,
      'total_revenue': instance.totalRevenue,
      'pending_appointments': instance.pendingAppointments,
      'completed_appointments': instance.completedAppointments,
    };
