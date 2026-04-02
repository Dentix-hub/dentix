import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../features/auth/data/datasources/auth_remote.dart';
import '../../features/auth/data/repositories/auth_repo_impl.dart';
import '../../features/auth/domain/repositories/auth_repository.dart';
import '../../features/auth/domain/usecases/change_password.dart';
import '../../features/auth/domain/usecases/login_usecase.dart';
import '../../features/auth/domain/usecases/logout_usecase.dart';
import '../../features/financial/data/datasources/financial_remote.dart';
import '../../features/financial/data/repositories/financial_repository_impl.dart';
import '../../features/financial/domain/repositories/financial_repository.dart';
import '../../features/financial/domain/usecases/get_financial_overview.dart';
import '../../features/financial/domain/usecases/record_payment.dart';
import '../../features/lab_orders/data/datasources/lab_order_remote.dart';
import '../../features/lab_orders/data/repositories/lab_order_repository_impl.dart';
import '../../features/lab_orders/domain/repositories/lab_order_repository.dart';
import '../../features/lab_orders/domain/usecases/create_lab_order.dart';
import '../../features/lab_orders/domain/usecases/get_lab_orders.dart';
import '../../features/prescriptions/data/datasources/prescription_remote.dart';
import '../../features/prescriptions/data/repositories/prescription_repository_impl.dart';
import '../../features/prescriptions/domain/repositories/prescription_repository.dart';
import '../../features/prescriptions/domain/usecases/create_prescription.dart';
import '../../features/prescriptions/domain/usecases/get_prescriptions.dart';
import '../network/auth_interceptor.dart';
import '../network/dio_client.dart';
import '../network/retry_interceptor.dart';

// ==================== CORE ====================

final secureStorageProvider = Provider((ref) => const FlutterSecureStorage());

final authInterceptorProvider = Provider((ref) {
  return AuthInterceptor(
    secureStorage: ref.watch(secureStorageProvider),
  );
});

final dioProvider = Provider<Dio>((ref) {
  final dio = DioClient.dio;
  
  // Add interceptors safely
  bool hasAuthInterceptor = dio.interceptors.any((i) => i is AuthInterceptor);
  if (!hasAuthInterceptor) {
    dio.interceptors.add(ref.watch(authInterceptorProvider));
  }
  
  bool hasRetryInterceptor = dio.interceptors.any((i) => i is RetryInterceptor);
  if (!hasRetryInterceptor) {
    dio.interceptors.add(RetryInterceptor());
  }
  
  // Configure base URL
  String baseUrl = 'http://127.0.0.1:8000';
  if (!kIsWeb && Platform.isAndroid) {
    baseUrl = 'http://10.0.2.2:8000';
  }
  
  DioClient.configureBaseUrl(baseUrl);
  
  return dio;
});

// ==================== AUTH ====================

final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  return AuthRemoteDataSourceImpl(dio: ref.watch(dioProvider));
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    authInterceptor: ref.watch(authInterceptorProvider),
  );
});

final loginUseCaseProvider = Provider<LoginUseCase>((ref) {
  return LoginUseCase(repository: ref.watch(authRepositoryProvider));
});

final logoutUseCaseProvider = Provider<LogoutUseCase>((ref) {
  return LogoutUseCase(repository: ref.watch(authRepositoryProvider));
});

final changePasswordUseCaseProvider = Provider<ChangePasswordUseCase>((ref) {
  return ChangePasswordUseCase(ref.watch(authRepositoryProvider));
});

// ==================== FINANCIAL ====================

final financialRemoteDataSourceProvider = Provider<FinancialRemoteDataSource>((ref) {
  return FinancialRemoteDataSource();
});

final financialRepositoryProvider = Provider<FinancialRepository>((ref) {
  return FinancialRepositoryImpl(ref.watch(financialRemoteDataSourceProvider));
});

final getFinancialOverviewUseCaseProvider = Provider<GetFinancialOverviewUseCase>((ref) {
  return GetFinancialOverviewUseCase(ref.watch(financialRepositoryProvider));
});

final recordPaymentUseCaseProvider = Provider<RecordPaymentUseCase>((ref) {
  return RecordPaymentUseCase(ref.watch(financialRepositoryProvider));
});

// ==================== PRESCRIPTIONS ====================

final prescriptionRemoteDataSourceProvider = Provider<PrescriptionRemoteDataSource>((ref) {
  return PrescriptionRemoteDataSource();
});

final prescriptionRepositoryProvider = Provider<PrescriptionRepository>((ref) {
  return PrescriptionRepositoryImpl(ref.watch(prescriptionRemoteDataSourceProvider));
});

final getPrescriptionsUseCaseProvider = Provider<GetPrescriptionsUseCase>((ref) {
  return GetPrescriptionsUseCase(ref.watch(prescriptionRepositoryProvider));
});

final createPrescriptionUseCaseProvider = Provider<CreatePrescriptionUseCase>((ref) {
  return CreatePrescriptionUseCase(ref.watch(prescriptionRepositoryProvider));
});

// ==================== LAB ORDERS ====================

final labOrderRemoteDataSourceProvider = Provider<LabOrderRemoteDataSource>((ref) {
  return LabOrderRemoteDataSource();
});

final labOrderRepositoryProvider = Provider<LabOrderRepository>((ref) {
  return LabOrderRepositoryImpl(ref.watch(labOrderRemoteDataSourceProvider));
});

final getLabOrdersUseCaseProvider = Provider<GetLabOrdersUseCase>((ref) {
  return GetLabOrdersUseCase(ref.watch(labOrderRepositoryProvider));
});

final createLabOrderUseCaseProvider = Provider<CreateLabOrderUseCase>((ref) {
  return CreateLabOrderUseCase(ref.watch(labOrderRepositoryProvider));
});
