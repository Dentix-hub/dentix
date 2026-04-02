// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'dashboard_stats_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

DashboardStatsModel _$DashboardStatsModelFromJson(Map<String, dynamic> json) {
  return _DashboardStatsModel.fromJson(json);
}

/// @nodoc
mixin _$DashboardStatsModel {
  @JsonKey(name: 'total_patients')
  int get totalPatients => throw _privateConstructorUsedError;
  @JsonKey(name: 'today_appointments')
  int get todayAppointments => throw _privateConstructorUsedError;
  @JsonKey(name: 'today_revenue')
  double get todayRevenue => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_revenue')
  double? get totalRevenue => throw _privateConstructorUsedError;
  @JsonKey(name: 'pending_appointments')
  int? get pendingAppointments => throw _privateConstructorUsedError;
  @JsonKey(name: 'completed_appointments')
  int? get completedAppointments => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $DashboardStatsModelCopyWith<DashboardStatsModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardStatsModelCopyWith<$Res> {
  factory $DashboardStatsModelCopyWith(
          DashboardStatsModel value, $Res Function(DashboardStatsModel) then) =
      _$DashboardStatsModelCopyWithImpl<$Res, DashboardStatsModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'total_patients') int totalPatients,
      @JsonKey(name: 'today_appointments') int todayAppointments,
      @JsonKey(name: 'today_revenue') double todayRevenue,
      @JsonKey(name: 'total_revenue') double? totalRevenue,
      @JsonKey(name: 'pending_appointments') int? pendingAppointments,
      @JsonKey(name: 'completed_appointments') int? completedAppointments});
}

/// @nodoc
class _$DashboardStatsModelCopyWithImpl<$Res, $Val extends DashboardStatsModel>
    implements $DashboardStatsModelCopyWith<$Res> {
  _$DashboardStatsModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalPatients = null,
    Object? todayAppointments = null,
    Object? todayRevenue = null,
    Object? totalRevenue = freezed,
    Object? pendingAppointments = freezed,
    Object? completedAppointments = freezed,
  }) {
    return _then(_value.copyWith(
      totalPatients: null == totalPatients
          ? _value.totalPatients
          : totalPatients // ignore: cast_nullable_to_non_nullable
              as int,
      todayAppointments: null == todayAppointments
          ? _value.todayAppointments
          : todayAppointments // ignore: cast_nullable_to_non_nullable
              as int,
      todayRevenue: null == todayRevenue
          ? _value.todayRevenue
          : todayRevenue // ignore: cast_nullable_to_non_nullable
              as double,
      totalRevenue: freezed == totalRevenue
          ? _value.totalRevenue
          : totalRevenue // ignore: cast_nullable_to_non_nullable
              as double?,
      pendingAppointments: freezed == pendingAppointments
          ? _value.pendingAppointments
          : pendingAppointments // ignore: cast_nullable_to_non_nullable
              as int?,
      completedAppointments: freezed == completedAppointments
          ? _value.completedAppointments
          : completedAppointments // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DashboardStatsModelImplCopyWith<$Res>
    implements $DashboardStatsModelCopyWith<$Res> {
  factory _$$DashboardStatsModelImplCopyWith(_$DashboardStatsModelImpl value,
          $Res Function(_$DashboardStatsModelImpl) then) =
      __$$DashboardStatsModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'total_patients') int totalPatients,
      @JsonKey(name: 'today_appointments') int todayAppointments,
      @JsonKey(name: 'today_revenue') double todayRevenue,
      @JsonKey(name: 'total_revenue') double? totalRevenue,
      @JsonKey(name: 'pending_appointments') int? pendingAppointments,
      @JsonKey(name: 'completed_appointments') int? completedAppointments});
}

/// @nodoc
class __$$DashboardStatsModelImplCopyWithImpl<$Res>
    extends _$DashboardStatsModelCopyWithImpl<$Res, _$DashboardStatsModelImpl>
    implements _$$DashboardStatsModelImplCopyWith<$Res> {
  __$$DashboardStatsModelImplCopyWithImpl(_$DashboardStatsModelImpl _value,
      $Res Function(_$DashboardStatsModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalPatients = null,
    Object? todayAppointments = null,
    Object? todayRevenue = null,
    Object? totalRevenue = freezed,
    Object? pendingAppointments = freezed,
    Object? completedAppointments = freezed,
  }) {
    return _then(_$DashboardStatsModelImpl(
      totalPatients: null == totalPatients
          ? _value.totalPatients
          : totalPatients // ignore: cast_nullable_to_non_nullable
              as int,
      todayAppointments: null == todayAppointments
          ? _value.todayAppointments
          : todayAppointments // ignore: cast_nullable_to_non_nullable
              as int,
      todayRevenue: null == todayRevenue
          ? _value.todayRevenue
          : todayRevenue // ignore: cast_nullable_to_non_nullable
              as double,
      totalRevenue: freezed == totalRevenue
          ? _value.totalRevenue
          : totalRevenue // ignore: cast_nullable_to_non_nullable
              as double?,
      pendingAppointments: freezed == pendingAppointments
          ? _value.pendingAppointments
          : pendingAppointments // ignore: cast_nullable_to_non_nullable
              as int?,
      completedAppointments: freezed == completedAppointments
          ? _value.completedAppointments
          : completedAppointments // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DashboardStatsModelImpl implements _DashboardStatsModel {
  const _$DashboardStatsModelImpl(
      {@JsonKey(name: 'total_patients') required this.totalPatients,
      @JsonKey(name: 'today_appointments') required this.todayAppointments,
      @JsonKey(name: 'today_revenue') required this.todayRevenue,
      @JsonKey(name: 'total_revenue') this.totalRevenue,
      @JsonKey(name: 'pending_appointments') this.pendingAppointments,
      @JsonKey(name: 'completed_appointments') this.completedAppointments});

  factory _$DashboardStatsModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$DashboardStatsModelImplFromJson(json);

  @override
  @JsonKey(name: 'total_patients')
  final int totalPatients;
  @override
  @JsonKey(name: 'today_appointments')
  final int todayAppointments;
  @override
  @JsonKey(name: 'today_revenue')
  final double todayRevenue;
  @override
  @JsonKey(name: 'total_revenue')
  final double? totalRevenue;
  @override
  @JsonKey(name: 'pending_appointments')
  final int? pendingAppointments;
  @override
  @JsonKey(name: 'completed_appointments')
  final int? completedAppointments;

  @override
  String toString() {
    return 'DashboardStatsModel(totalPatients: $totalPatients, todayAppointments: $todayAppointments, todayRevenue: $todayRevenue, totalRevenue: $totalRevenue, pendingAppointments: $pendingAppointments, completedAppointments: $completedAppointments)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardStatsModelImpl &&
            (identical(other.totalPatients, totalPatients) ||
                other.totalPatients == totalPatients) &&
            (identical(other.todayAppointments, todayAppointments) ||
                other.todayAppointments == todayAppointments) &&
            (identical(other.todayRevenue, todayRevenue) ||
                other.todayRevenue == todayRevenue) &&
            (identical(other.totalRevenue, totalRevenue) ||
                other.totalRevenue == totalRevenue) &&
            (identical(other.pendingAppointments, pendingAppointments) ||
                other.pendingAppointments == pendingAppointments) &&
            (identical(other.completedAppointments, completedAppointments) ||
                other.completedAppointments == completedAppointments));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, totalPatients, todayAppointments,
      todayRevenue, totalRevenue, pendingAppointments, completedAppointments);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardStatsModelImplCopyWith<_$DashboardStatsModelImpl> get copyWith =>
      __$$DashboardStatsModelImplCopyWithImpl<_$DashboardStatsModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DashboardStatsModelImplToJson(
      this,
    );
  }
}

abstract class _DashboardStatsModel implements DashboardStatsModel {
  const factory _DashboardStatsModel(
      {@JsonKey(name: 'total_patients') required final int totalPatients,
      @JsonKey(name: 'today_appointments') required final int todayAppointments,
      @JsonKey(name: 'today_revenue') required final double todayRevenue,
      @JsonKey(name: 'total_revenue') final double? totalRevenue,
      @JsonKey(name: 'pending_appointments') final int? pendingAppointments,
      @JsonKey(name: 'completed_appointments')
      final int? completedAppointments}) = _$DashboardStatsModelImpl;

  factory _DashboardStatsModel.fromJson(Map<String, dynamic> json) =
      _$DashboardStatsModelImpl.fromJson;

  @override
  @JsonKey(name: 'total_patients')
  int get totalPatients;
  @override
  @JsonKey(name: 'today_appointments')
  int get todayAppointments;
  @override
  @JsonKey(name: 'today_revenue')
  double get todayRevenue;
  @override
  @JsonKey(name: 'total_revenue')
  double? get totalRevenue;
  @override
  @JsonKey(name: 'pending_appointments')
  int? get pendingAppointments;
  @override
  @JsonKey(name: 'completed_appointments')
  int? get completedAppointments;
  @override
  @JsonKey(ignore: true)
  _$$DashboardStatsModelImplCopyWith<_$DashboardStatsModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
