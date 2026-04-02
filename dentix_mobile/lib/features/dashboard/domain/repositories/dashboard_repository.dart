import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/dashboard_entity.dart';

abstract class DashboardRepository {
  Future<Either<Failure, DashboardStatsEntity>> getDashboardStats();
}
