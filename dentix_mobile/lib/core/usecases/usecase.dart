import 'package:dartz/dartz.dart';

import '../error/failures.dart';

/// Abstract class for use cases
/// 
/// [Type] - The return type of the use case
/// [Params] - The parameters type for the use case
abstract class UseCase<Type, Params> {
  Future<Either<Failure, Type>> call(Params params);
}

/// Use case without parameters
abstract class NoParamsUseCase<Type> {
  Future<Either<Failure, Type>> call();
}
