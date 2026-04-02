// ignore_for_file: invalid_annotation_target
import 'package:freezed_annotation/freezed_annotation.dart';

part 'dashboard_stats_model.freezed.dart';
part 'dashboard_stats_model.g.dart';

@freezed
class DashboardStatsModel with _$DashboardStatsModel {
  const factory DashboardStatsModel({
    @JsonKey(name: 'total_patients') required int totalPatients,
    @JsonKey(name: 'total_appointments_today') required int todayAppointments,
    @JsonKey(name: 'today_revenue') required double todayRevenue,
    @JsonKey(name: 'total_revenue') double? totalRevenue,
    @JsonKey(name: 'pending_appointments') int? pendingAppointments,
    @JsonKey(name: 'completed_appointments') int? completedAppointments,
  }) = _DashboardStatsModel;

  factory DashboardStatsModel.fromJson(Map<String, dynamic> json) =>
      _$DashboardStatsModelFromJson(json);
}
