import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/dashboard_entity.dart';
import '../repositories/dashboard_repository.dart';

class GetDashboardStatsUseCase {
  final DashboardRepository repository;

  GetDashboardStatsUseCase({required this.repository});

  Future<Either<Failure, DashboardStatsEntity>> call() async {
    return await repository.getDashboardStats();
  }
}
