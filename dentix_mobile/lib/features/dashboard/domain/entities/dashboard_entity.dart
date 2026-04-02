class DashboardStatsEntity {
  final int totalPatients;
  final int todayAppointments;
  final double todayRevenue;
  final double? totalRevenue;
  final int? pendingAppointments;
  final int? completedAppointments;

  const DashboardStatsEntity({
    required this.totalPatients,
    required this.todayAppointments,
    required this.todayRevenue,
    this.totalRevenue,
    this.pendingAppointments,
    this.completedAppointments,
  });
}
