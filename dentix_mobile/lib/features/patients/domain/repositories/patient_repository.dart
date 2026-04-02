import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/patient_entity.dart';

abstract class PatientRepository {
  Future<Either<Failure, PatientListEntity>> getPatients({
    required int page,
    required int limit,
    String? search,
  });
  
  Future<Either<Failure, PatientEntity>> getPatientById(int id);

  Future<Either<Failure, PatientEntity>> createPatient({
    required String fullName,
    required String phone,
    String? email,
    String? gender,
    String? birthDate,
    String? address,
    String? medicalHistory,
    String? allergies,
  });
}
