class AppointmentEntity {
  final int id;
  final int patientId;
  final String? patientName;
  final int dentistId;
  final String? dentistName;
  final String appointmentDate;
  final String startTime;
  final String? endTime;
  final String status;
  final String? notes;
  final String? procedureType;
  final String? createdAt;
  final String? updatedAt;

  const AppointmentEntity({
    required this.id,
    required this.patientId,
    this.patientName,
    required this.dentistId,
    this.dentistName,
    required this.appointmentDate,
    required this.startTime,
    this.endTime,
    required this.status,
    this.notes,
    this.procedureType,
    this.createdAt,
    this.updatedAt,
  });

  /// Returns true if the appointment is scheduled for today
  bool get isToday {
    final now = DateTime.now();
    final date = DateTime.tryParse(appointmentDate);
    if (date == null) return false;
    return date.year == now.year && 
           date.month == now.month && 
           date.day == now.day;
  }

  /// Returns true if the appointment date is in the past
  bool get isPast {
    final now = DateTime.now();
    final date = DateTime.tryParse(appointmentDate);
    if (date == null) return false;
    return date.isBefore(DateTime(now.year, now.month, now.day));
  }

  /// Returns true if the appointment date is in the future
  bool get isFuture {
    final now = DateTime.now();
    final date = DateTime.tryParse(appointmentDate);
    if (date == null) return false;
    return date.isAfter(DateTime(now.year, now.month, now.day));
  }
}

class AppointmentListEntity {
  final List<AppointmentEntity> items;
  final int total;
  final int currentPage;
  final int totalPages;

  const AppointmentListEntity({
    required this.items,
    required this.total,
    required this.currentPage,
    required this.totalPages,
  });
}
