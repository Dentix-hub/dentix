import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/error/exceptions.dart';
import '../../domain/entities/treatment_entity.dart';
import '../../domain/repositories/treatment_repository.dart';
import '../datasources/treatment_remote.dart';
import '../models/treatment_model.dart';

class TreatmentRepositoryImpl implements TreatmentRepository {
  final TreatmentRemoteDataSource remoteDataSource;

  TreatmentRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, TreatmentListEntity>> getTreatmentsByPatientId({
    required int patientId,
    required int page,
    required int limit,
  }) async {
    try {
      final result = await remoteDataSource.getTreatmentsByPatientId(
        patientId: patientId,
        page: page,
        limit: limit,
      );
      return Right(_mapListResponseToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, TreatmentEntity>> getTreatmentById(int id) async {
    try {
      final result = await remoteDataSource.getTreatmentById(id);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  TreatmentListEntity _mapListResponseToEntity(TreatmentListResponse response) {
    return TreatmentListEntity(
      items: response.items.map(_mapModelToEntity).toList(),
      total: response.total,
      currentPage: response.currentPage,
      totalPages: response.totalPages,
    );
  }

  TreatmentEntity _mapModelToEntity(TreatmentModel model) {
    return TreatmentEntity(
      id: model.id,
      patientId: model.patientId,
      appointmentId: model.appointmentId,
      procedureType: model.procedureType,
      description: model.description,
      cost: model.cost,
      status: model.status,
      treatmentDate: model.treatmentDate,
      createdAt: model.createdAt,
      updatedAt: model.updatedAt,
    );
  }
}
