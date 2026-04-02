import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/error/exceptions.dart';
import '../models/dashboard_stats_model.dart';

abstract class DashboardRemoteDataSource {
  Future<DashboardStatsModel> getDashboardStats();
}

class DashboardRemoteDataSourceImpl implements DashboardRemoteDataSource {
  final Dio dio;

  DashboardRemoteDataSourceImpl({required this.dio});

  @override
  Future<DashboardStatsModel> getDashboardStats() async {
    try {
      final response = await dio.get(ApiEndpoints.dashboardStats);

      if (response.statusCode == 200) {
        return DashboardStatsModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load dashboard stats',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ServerException(
        message: e.response?.data?['message'] ?? 'Network error',
        code: e.response?.statusCode,
      );
    }
  }
}
