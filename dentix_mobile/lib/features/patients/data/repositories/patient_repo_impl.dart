import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/error/exceptions.dart';
import '../../domain/entities/patient_entity.dart';
import '../../domain/repositories/patient_repository.dart';
import '../datasources/patient_remote.dart';
import '../models/patient_model.dart';

class PatientRepositoryImpl implements PatientRepository {
  final PatientRemoteDataSource remoteDataSource;

  PatientRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, PatientListEntity>> getPatients({
    required int page,
    required int limit,
    String? search,
  }) async {
    try {
      final result = await remoteDataSource.getPatients(
        page: page,
        limit: limit,
        search: search,
      );
      return Right(_mapListResponseToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PatientEntity>> getPatientById(int id) async {
    try {
      final result = await remoteDataSource.getPatientById(id);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  PatientListEntity _mapListResponseToEntity(PatientListResponse response) {
    return PatientListEntity(
      items: response.items.map(_mapModelToEntity).toList(),
      total: response.total,
      currentPage: response.currentPage,
      totalPages: response.totalPages,
      pageSize: response.pageSize,
    );
  }

  PatientEntity _mapModelToEntity(PatientModel model) {
    return PatientEntity(
      id: model.id,
      fullName: model.fullName,
      phone: model.phone,
      email: model.email,
      dateOfBirth: model.dateOfBirth,
      gender: model.gender,
      address: model.address,
      medicalHistory: model.medicalHistory,
      allergies: model.allergies,
      createdAt: model.createdAt,
      updatedAt: model.updatedAt,
    );
  }


  @override
  Future<Either<Failure, PatientEntity>> createPatient({
    required String fullName,
    required String phone,
    String? email,
    String? gender,
    String? birthDate,
    String? address,
    String? medicalHistory,
    String? allergies,
  }) async {
    try {
      final data = {
        'full_name': fullName,
        'phone': phone,
        'email': email,
        'gender': gender,
        'date_of_birth': birthDate,
        'address': address,
        'medical_history': medicalHistory,
        'allergies': allergies,
      };
      
      // Remove nulls strictly if backend hates them, or keep them.
      // Usually backend ignores nulls or expects them.
      data.removeWhere((key, value) => value == null);

      final result = await remoteDataSource.createPatient(data);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }
}
