import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/error/exceptions.dart';
import '../../domain/entities/dashboard_entity.dart';
import '../../domain/repositories/dashboard_repository.dart';
import '../datasources/dashboard_remote.dart';
import '../models/dashboard_stats_model.dart';

class DashboardRepositoryImpl implements DashboardRepository {
  final DashboardRemoteDataSource remoteDataSource;

  DashboardRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, DashboardStatsEntity>> getDashboardStats() async {
    try {
      final result = await remoteDataSource.getDashboardStats();
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  DashboardStatsEntity _mapModelToEntity(DashboardStatsModel model) {
    return DashboardStatsEntity(
      totalPatients: model.totalPatients,
      todayAppointments: model.todayAppointments,
      todayRevenue: model.todayRevenue,
      totalRevenue: model.totalRevenue,
      pendingAppointments: model.pendingAppointments,
      completedAppointments: model.completedAppointments,
    );
  }
}
