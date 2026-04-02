// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'treatment_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

TreatmentModel _$TreatmentModelFromJson(Map<String, dynamic> json) {
  return _TreatmentModel.fromJson(json);
}

/// @nodoc
mixin _$TreatmentModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'appointment_id')
  int? get appointmentId => throw _privateConstructorUsedError;
  @JsonKey(name: 'procedure_type')
  String get procedureType => throw _privateConstructorUsedError;
  @JsonKey(name: 'description')
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'cost')
  double get cost => throw _privateConstructorUsedError;
  @JsonKey(name: 'status')
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'treatment_date')
  String get treatmentDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $TreatmentModelCopyWith<TreatmentModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TreatmentModelCopyWith<$Res> {
  factory $TreatmentModelCopyWith(
          TreatmentModel value, $Res Function(TreatmentModel) then) =
      _$TreatmentModelCopyWithImpl<$Res, TreatmentModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'procedure_type') String procedureType,
      @JsonKey(name: 'description') String? description,
      @JsonKey(name: 'cost') double cost,
      @JsonKey(name: 'status') String status,
      @JsonKey(name: 'treatment_date') String treatmentDate,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$TreatmentModelCopyWithImpl<$Res, $Val extends TreatmentModel>
    implements $TreatmentModelCopyWith<$Res> {
  _$TreatmentModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? appointmentId = freezed,
    Object? procedureType = null,
    Object? description = freezed,
    Object? cost = null,
    Object? status = null,
    Object? treatmentDate = null,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      procedureType: null == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      cost: null == cost
          ? _value.cost
          : cost // ignore: cast_nullable_to_non_nullable
              as double,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      treatmentDate: null == treatmentDate
          ? _value.treatmentDate
          : treatmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String?,
      updatedAt: freezed == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$TreatmentModelImplCopyWith<$Res>
    implements $TreatmentModelCopyWith<$Res> {
  factory _$$TreatmentModelImplCopyWith(_$TreatmentModelImpl value,
          $Res Function(_$TreatmentModelImpl) then) =
      __$$TreatmentModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'procedure_type') String procedureType,
      @JsonKey(name: 'description') String? description,
      @JsonKey(name: 'cost') double cost,
      @JsonKey(name: 'status') String status,
      @JsonKey(name: 'treatment_date') String treatmentDate,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$TreatmentModelImplCopyWithImpl<$Res>
    extends _$TreatmentModelCopyWithImpl<$Res, _$TreatmentModelImpl>
    implements _$$TreatmentModelImplCopyWith<$Res> {
  __$$TreatmentModelImplCopyWithImpl(
      _$TreatmentModelImpl _value, $Res Function(_$TreatmentModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? appointmentId = freezed,
    Object? procedureType = null,
    Object? description = freezed,
    Object? cost = null,
    Object? status = null,
    Object? treatmentDate = null,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$TreatmentModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      procedureType: null == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      cost: null == cost
          ? _value.cost
          : cost // ignore: cast_nullable_to_non_nullable
              as double,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      treatmentDate: null == treatmentDate
          ? _value.treatmentDate
          : treatmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String?,
      updatedAt: freezed == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$TreatmentModelImpl implements _TreatmentModel {
  const _$TreatmentModelImpl(
      {required this.id,
      @JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'appointment_id') this.appointmentId,
      @JsonKey(name: 'procedure_type') required this.procedureType,
      @JsonKey(name: 'description') this.description,
      @JsonKey(name: 'cost') required this.cost,
      @JsonKey(name: 'status') required this.status,
      @JsonKey(name: 'treatment_date') required this.treatmentDate,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt});

  factory _$TreatmentModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$TreatmentModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  @override
  @JsonKey(name: 'appointment_id')
  final int? appointmentId;
  @override
  @JsonKey(name: 'procedure_type')
  final String procedureType;
  @override
  @JsonKey(name: 'description')
  final String? description;
  @override
  @JsonKey(name: 'cost')
  final double cost;
  @override
  @JsonKey(name: 'status')
  final String status;
  @override
  @JsonKey(name: 'treatment_date')
  final String treatmentDate;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'TreatmentModel(id: $id, patientId: $patientId, appointmentId: $appointmentId, procedureType: $procedureType, description: $description, cost: $cost, status: $status, treatmentDate: $treatmentDate, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TreatmentModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.appointmentId, appointmentId) ||
                other.appointmentId == appointmentId) &&
            (identical(other.procedureType, procedureType) ||
                other.procedureType == procedureType) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.cost, cost) || other.cost == cost) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.treatmentDate, treatmentDate) ||
                other.treatmentDate == treatmentDate) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.updatedAt, updatedAt) ||
                other.updatedAt == updatedAt));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      patientId,
      appointmentId,
      procedureType,
      description,
      cost,
      status,
      treatmentDate,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$TreatmentModelImplCopyWith<_$TreatmentModelImpl> get copyWith =>
      __$$TreatmentModelImplCopyWithImpl<_$TreatmentModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TreatmentModelImplToJson(
      this,
    );
  }
}

abstract class _TreatmentModel implements TreatmentModel {
  const factory _TreatmentModel(
          {required final int id,
          @JsonKey(name: 'patient_id') required final int patientId,
          @JsonKey(name: 'appointment_id') final int? appointmentId,
          @JsonKey(name: 'procedure_type') required final String procedureType,
          @JsonKey(name: 'description') final String? description,
          @JsonKey(name: 'cost') required final double cost,
          @JsonKey(name: 'status') required final String status,
          @JsonKey(name: 'treatment_date') required final String treatmentDate,
          @JsonKey(name: 'created_at') final String? createdAt,
          @JsonKey(name: 'updated_at') final String? updatedAt}) =
      _$TreatmentModelImpl;

  factory _TreatmentModel.fromJson(Map<String, dynamic> json) =
      _$TreatmentModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  @JsonKey(name: 'appointment_id')
  int? get appointmentId;
  @override
  @JsonKey(name: 'procedure_type')
  String get procedureType;
  @override
  @JsonKey(name: 'description')
  String? get description;
  @override
  @JsonKey(name: 'cost')
  double get cost;
  @override
  @JsonKey(name: 'status')
  String get status;
  @override
  @JsonKey(name: 'treatment_date')
  String get treatmentDate;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$TreatmentModelImplCopyWith<_$TreatmentModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

TreatmentListResponse _$TreatmentListResponseFromJson(
    Map<String, dynamic> json) {
  return _TreatmentListResponse.fromJson(json);
}

/// @nodoc
mixin _$TreatmentListResponse {
  List<TreatmentModel> get items => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;
  @JsonKey(name: 'page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'pages')
  int get totalPages => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $TreatmentListResponseCopyWith<TreatmentListResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TreatmentListResponseCopyWith<$Res> {
  factory $TreatmentListResponseCopyWith(TreatmentListResponse value,
          $Res Function(TreatmentListResponse) then) =
      _$TreatmentListResponseCopyWithImpl<$Res, TreatmentListResponse>;
  @useResult
  $Res call(
      {List<TreatmentModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages});
}

/// @nodoc
class _$TreatmentListResponseCopyWithImpl<$Res,
        $Val extends TreatmentListResponse>
    implements $TreatmentListResponseCopyWith<$Res> {
  _$TreatmentListResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? currentPage = null,
    Object? totalPages = null,
  }) {
    return _then(_value.copyWith(
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<TreatmentModel>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      currentPage: null == currentPage
          ? _value.currentPage
          : currentPage // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$TreatmentListResponseImplCopyWith<$Res>
    implements $TreatmentListResponseCopyWith<$Res> {
  factory _$$TreatmentListResponseImplCopyWith(
          _$TreatmentListResponseImpl value,
          $Res Function(_$TreatmentListResponseImpl) then) =
      __$$TreatmentListResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<TreatmentModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages});
}

/// @nodoc
class __$$TreatmentListResponseImplCopyWithImpl<$Res>
    extends _$TreatmentListResponseCopyWithImpl<$Res,
        _$TreatmentListResponseImpl>
    implements _$$TreatmentListResponseImplCopyWith<$Res> {
  __$$TreatmentListResponseImplCopyWithImpl(_$TreatmentListResponseImpl _value,
      $Res Function(_$TreatmentListResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? currentPage = null,
    Object? totalPages = null,
  }) {
    return _then(_$TreatmentListResponseImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<TreatmentModel>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      currentPage: null == currentPage
          ? _value.currentPage
          : currentPage // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$TreatmentListResponseImpl implements _TreatmentListResponse {
  const _$TreatmentListResponseImpl(
      {required final List<TreatmentModel> items,
      required this.total,
      @JsonKey(name: 'page') required this.currentPage,
      @JsonKey(name: 'pages') required this.totalPages})
      : _items = items;

  factory _$TreatmentListResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$TreatmentListResponseImplFromJson(json);

  final List<TreatmentModel> _items;
  @override
  List<TreatmentModel> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final int total;
  @override
  @JsonKey(name: 'page')
  final int currentPage;
  @override
  @JsonKey(name: 'pages')
  final int totalPages;

  @override
  String toString() {
    return 'TreatmentListResponse(items: $items, total: $total, currentPage: $currentPage, totalPages: $totalPages)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TreatmentListResponseImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.total, total) || other.total == total) &&
            (identical(other.currentPage, currentPage) ||
                other.currentPage == currentPage) &&
            (identical(other.totalPages, totalPages) ||
                other.totalPages == totalPages));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_items),
      total,
      currentPage,
      totalPages);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$TreatmentListResponseImplCopyWith<_$TreatmentListResponseImpl>
      get copyWith => __$$TreatmentListResponseImplCopyWithImpl<
          _$TreatmentListResponseImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TreatmentListResponseImplToJson(
      this,
    );
  }
}

abstract class _TreatmentListResponse implements TreatmentListResponse {
  const factory _TreatmentListResponse(
          {required final List<TreatmentModel> items,
          required final int total,
          @JsonKey(name: 'page') required final int currentPage,
          @JsonKey(name: 'pages') required final int totalPages}) =
      _$TreatmentListResponseImpl;

  factory _TreatmentListResponse.fromJson(Map<String, dynamic> json) =
      _$TreatmentListResponseImpl.fromJson;

  @override
  List<TreatmentModel> get items;
  @override
  int get total;
  @override
  @JsonKey(name: 'page')
  int get currentPage;
  @override
  @JsonKey(name: 'pages')
  int get totalPages;
  @override
  @JsonKey(ignore: true)
  _$$TreatmentListResponseImplCopyWith<_$TreatmentListResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}
