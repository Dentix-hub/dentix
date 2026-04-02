class PatientEntity {
  final int id;
  final String fullName;
  final String? phone;
  final String? email;
  final String? dateOfBirth;
  final String? gender;
  final String? address;
  final String? medicalHistory;
  final String? allergies;
  final String? createdAt;
  final String? updatedAt;

  const PatientEntity({
    required this.id,
    required this.fullName,
    this.phone,
    this.email,
    this.dateOfBirth,
    this.gender,
    this.address,
    this.medicalHistory,
    this.allergies,
    this.createdAt,
    this.updatedAt,
  });
}

class PatientListEntity {
  final List<PatientEntity> items;
  final int total;
  final int currentPage;
  final int totalPages;
  final int pageSize;

  const PatientListEntity({
    required this.items,
    required this.total,
    required this.currentPage,
    required this.totalPages,
    required this.pageSize,
  });
}
