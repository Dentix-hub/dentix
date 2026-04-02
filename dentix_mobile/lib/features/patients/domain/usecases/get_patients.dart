import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/patient_entity.dart';
import '../repositories/patient_repository.dart';

class GetPatientsUseCase {
  final PatientRepository repository;

  GetPatientsUseCase({required this.repository});

  Future<Either<Failure, PatientListEntity>> call({
    required int page,
    required int limit,
    String? search,
  }) async {
    return await repository.getPatients(
      page: page,
      limit: limit,
      search: search,
    );
  }
}

class GetPatientByIdUseCase {
  final PatientRepository repository;

  GetPatientByIdUseCase({required this.repository});

  Future<Either<Failure, PatientEntity>> call(int id) async {
    return await repository.getPatientById(id);
  }
}

class CreatePatientUseCase {
  final PatientRepository repository;

  CreatePatientUseCase({required this.repository});

  Future<Either<Failure, PatientEntity>> call({
    required String fullName,
    required String phone,
    String? email,
    String? gender,
    String? birthDate,
    String? address,
    String? medicalHistory,
    String? allergies,
  }) async {
    return await repository.createPatient(
      fullName: fullName,
      phone: phone,
      email: email,
      gender: gender,
      birthDate: birthDate,
      address: address,
      medicalHistory: medicalHistory,
      allergies: allergies,
    );
  }
}
