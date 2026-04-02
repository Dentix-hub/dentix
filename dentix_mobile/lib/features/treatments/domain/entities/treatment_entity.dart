class TreatmentEntity {
  final int id;
  final int patientId;
  final int? appointmentId;
  final String procedureType;
  final String? description;
  final double cost;
  final String status;
  final String treatmentDate;
  final String? createdAt;
  final String? updatedAt;

  const TreatmentEntity({
    required this.id,
    required this.patientId,
    this.appointmentId,
    required this.procedureType,
    this.description,
    required this.cost,
    required this.status,
    required this.treatmentDate,
    this.createdAt,
    this.updatedAt,
  });
}

class TreatmentListEntity {
  final List<TreatmentEntity> items;
  final int total;
  final int currentPage;
  final int totalPages;

  const TreatmentListEntity({
    required this.items,
    required this.total,
    required this.currentPage,
    required this.totalPages,
  });
}
