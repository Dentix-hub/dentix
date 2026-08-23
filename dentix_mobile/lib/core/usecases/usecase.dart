import 'package:dartz/dartz.dart';

import '../error/failures.dart';

/// Abstract class for use cases
///
/// [Result] - The return type of the use case
/// [Params] - The parameters type for the use case
abstract class UseCase<Result, Params> {
  Future<Either<Failure, Result>> call(Params params);
}

/// Use case without parameters
abstract class NoParamsUseCase<Result> {
  Future<Either<Failure, Result>> call();
}
