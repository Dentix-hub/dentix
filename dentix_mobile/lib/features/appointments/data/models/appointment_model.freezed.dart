// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'appointment_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

AppointmentModel _$AppointmentModelFromJson(Map<String, dynamic> json) {
  return _AppointmentModel.fromJson(json);
}

/// @nodoc
mixin _$AppointmentModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_name')
  String? get patientName => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_id')
  int get dentistId => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_name')
  String? get dentistName => throw _privateConstructorUsedError;
  @JsonKey(name: 'appointment_date')
  String get appointmentDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_time')
  String get startTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_time')
  String? get endTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'status')
  String get status =>
      throw _privateConstructorUsedError; // scheduled, completed, cancelled, no_show
  @JsonKey(name: 'notes')
  String? get notes => throw _privateConstructorUsedError;
  @JsonKey(name: 'procedure_type')
  String? get procedureType => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $AppointmentModelCopyWith<AppointmentModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AppointmentModelCopyWith<$Res> {
  factory $AppointmentModelCopyWith(
          AppointmentModel value, $Res Function(AppointmentModel) then) =
      _$AppointmentModelCopyWithImpl<$Res, AppointmentModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'appointment_date') String appointmentDate,
      @JsonKey(name: 'start_time') String startTime,
      @JsonKey(name: 'end_time') String? endTime,
      @JsonKey(name: 'status') String status,
      @JsonKey(name: 'notes') String? notes,
      @JsonKey(name: 'procedure_type') String? procedureType,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$AppointmentModelCopyWithImpl<$Res, $Val extends AppointmentModel>
    implements $AppointmentModelCopyWith<$Res> {
  _$AppointmentModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? patientName = freezed,
    Object? dentistId = null,
    Object? dentistName = freezed,
    Object? appointmentDate = null,
    Object? startTime = null,
    Object? endTime = freezed,
    Object? status = null,
    Object? notes = freezed,
    Object? procedureType = freezed,
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
      patientName: freezed == patientName
          ? _value.patientName
          : patientName // ignore: cast_nullable_to_non_nullable
              as String?,
      dentistId: null == dentistId
          ? _value.dentistId
          : dentistId // ignore: cast_nullable_to_non_nullable
              as int,
      dentistName: freezed == dentistName
          ? _value.dentistName
          : dentistName // ignore: cast_nullable_to_non_nullable
              as String?,
      appointmentDate: null == appointmentDate
          ? _value.appointmentDate
          : appointmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as String,
      endTime: freezed == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      procedureType: freezed == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String?,
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
abstract class _$$AppointmentModelImplCopyWith<$Res>
    implements $AppointmentModelCopyWith<$Res> {
  factory _$$AppointmentModelImplCopyWith(_$AppointmentModelImpl value,
          $Res Function(_$AppointmentModelImpl) then) =
      __$$AppointmentModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'appointment_date') String appointmentDate,
      @JsonKey(name: 'start_time') String startTime,
      @JsonKey(name: 'end_time') String? endTime,
      @JsonKey(name: 'status') String status,
      @JsonKey(name: 'notes') String? notes,
      @JsonKey(name: 'procedure_type') String? procedureType,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$AppointmentModelImplCopyWithImpl<$Res>
    extends _$AppointmentModelCopyWithImpl<$Res, _$AppointmentModelImpl>
    implements _$$AppointmentModelImplCopyWith<$Res> {
  __$$AppointmentModelImplCopyWithImpl(_$AppointmentModelImpl _value,
      $Res Function(_$AppointmentModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? patientName = freezed,
    Object? dentistId = null,
    Object? dentistName = freezed,
    Object? appointmentDate = null,
    Object? startTime = null,
    Object? endTime = freezed,
    Object? status = null,
    Object? notes = freezed,
    Object? procedureType = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$AppointmentModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      patientName: freezed == patientName
          ? _value.patientName
          : patientName // ignore: cast_nullable_to_non_nullable
              as String?,
      dentistId: null == dentistId
          ? _value.dentistId
          : dentistId // ignore: cast_nullable_to_non_nullable
              as int,
      dentistName: freezed == dentistName
          ? _value.dentistName
          : dentistName // ignore: cast_nullable_to_non_nullable
              as String?,
      appointmentDate: null == appointmentDate
          ? _value.appointmentDate
          : appointmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as String,
      endTime: freezed == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      procedureType: freezed == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String?,
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
class _$AppointmentModelImpl implements _AppointmentModel {
  const _$AppointmentModelImpl(
      {required this.id,
      @JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'patient_name') this.patientName,
      @JsonKey(name: 'dentist_id') required this.dentistId,
      @JsonKey(name: 'dentist_name') this.dentistName,
      @JsonKey(name: 'appointment_date') required this.appointmentDate,
      @JsonKey(name: 'start_time') required this.startTime,
      @JsonKey(name: 'end_time') this.endTime,
      @JsonKey(name: 'status') required this.status,
      @JsonKey(name: 'notes') this.notes,
      @JsonKey(name: 'procedure_type') this.procedureType,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt});

  factory _$AppointmentModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$AppointmentModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  @override
  @JsonKey(name: 'patient_name')
  final String? patientName;
  @override
  @JsonKey(name: 'dentist_id')
  final int dentistId;
  @override
  @JsonKey(name: 'dentist_name')
  final String? dentistName;
  @override
  @JsonKey(name: 'appointment_date')
  final String appointmentDate;
  @override
  @JsonKey(name: 'start_time')
  final String startTime;
  @override
  @JsonKey(name: 'end_time')
  final String? endTime;
  @override
  @JsonKey(name: 'status')
  final String status;
// scheduled, completed, cancelled, no_show
  @override
  @JsonKey(name: 'notes')
  final String? notes;
  @override
  @JsonKey(name: 'procedure_type')
  final String? procedureType;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'AppointmentModel(id: $id, patientId: $patientId, patientName: $patientName, dentistId: $dentistId, dentistName: $dentistName, appointmentDate: $appointmentDate, startTime: $startTime, endTime: $endTime, status: $status, notes: $notes, procedureType: $procedureType, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AppointmentModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.patientName, patientName) ||
                other.patientName == patientName) &&
            (identical(other.dentistId, dentistId) ||
                other.dentistId == dentistId) &&
            (identical(other.dentistName, dentistName) ||
                other.dentistName == dentistName) &&
            (identical(other.appointmentDate, appointmentDate) ||
                other.appointmentDate == appointmentDate) &&
            (identical(other.startTime, startTime) ||
                other.startTime == startTime) &&
            (identical(other.endTime, endTime) || other.endTime == endTime) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.procedureType, procedureType) ||
                other.procedureType == procedureType) &&
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
      patientName,
      dentistId,
      dentistName,
      appointmentDate,
      startTime,
      endTime,
      status,
      notes,
      procedureType,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$AppointmentModelImplCopyWith<_$AppointmentModelImpl> get copyWith =>
      __$$AppointmentModelImplCopyWithImpl<_$AppointmentModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AppointmentModelImplToJson(
      this,
    );
  }
}

abstract class _AppointmentModel implements AppointmentModel {
  const factory _AppointmentModel(
      {required final int id,
      @JsonKey(name: 'patient_id') required final int patientId,
      @JsonKey(name: 'patient_name') final String? patientName,
      @JsonKey(name: 'dentist_id') required final int dentistId,
      @JsonKey(name: 'dentist_name') final String? dentistName,
      @JsonKey(name: 'appointment_date') required final String appointmentDate,
      @JsonKey(name: 'start_time') required final String startTime,
      @JsonKey(name: 'end_time') final String? endTime,
      @JsonKey(name: 'status') required final String status,
      @JsonKey(name: 'notes') final String? notes,
      @JsonKey(name: 'procedure_type') final String? procedureType,
      @JsonKey(name: 'created_at') final String? createdAt,
      @JsonKey(name: 'updated_at')
      final String? updatedAt}) = _$AppointmentModelImpl;

  factory _AppointmentModel.fromJson(Map<String, dynamic> json) =
      _$AppointmentModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  @JsonKey(name: 'patient_name')
  String? get patientName;
  @override
  @JsonKey(name: 'dentist_id')
  int get dentistId;
  @override
  @JsonKey(name: 'dentist_name')
  String? get dentistName;
  @override
  @JsonKey(name: 'appointment_date')
  String get appointmentDate;
  @override
  @JsonKey(name: 'start_time')
  String get startTime;
  @override
  @JsonKey(name: 'end_time')
  String? get endTime;
  @override
  @JsonKey(name: 'status')
  String get status;
  @override // scheduled, completed, cancelled, no_show
  @JsonKey(name: 'notes')
  String? get notes;
  @override
  @JsonKey(name: 'procedure_type')
  String? get procedureType;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$AppointmentModelImplCopyWith<_$AppointmentModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AppointmentListResponse _$AppointmentListResponseFromJson(
    Map<String, dynamic> json) {
  return _AppointmentListResponse.fromJson(json);
}

/// @nodoc
mixin _$AppointmentListResponse {
  List<AppointmentModel> get items => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;
  @JsonKey(name: 'page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'pages')
  int get totalPages => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $AppointmentListResponseCopyWith<AppointmentListResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AppointmentListResponseCopyWith<$Res> {
  factory $AppointmentListResponseCopyWith(AppointmentListResponse value,
          $Res Function(AppointmentListResponse) then) =
      _$AppointmentListResponseCopyWithImpl<$Res, AppointmentListResponse>;
  @useResult
  $Res call(
      {List<AppointmentModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages});
}

/// @nodoc
class _$AppointmentListResponseCopyWithImpl<$Res,
        $Val extends AppointmentListResponse>
    implements $AppointmentListResponseCopyWith<$Res> {
  _$AppointmentListResponseCopyWithImpl(this._value, this._then);

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
              as List<AppointmentModel>,
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
abstract class _$$AppointmentListResponseImplCopyWith<$Res>
    implements $AppointmentListResponseCopyWith<$Res> {
  factory _$$AppointmentListResponseImplCopyWith(
          _$AppointmentListResponseImpl value,
          $Res Function(_$AppointmentListResponseImpl) then) =
      __$$AppointmentListResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<AppointmentModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages});
}

/// @nodoc
class __$$AppointmentListResponseImplCopyWithImpl<$Res>
    extends _$AppointmentListResponseCopyWithImpl<$Res,
        _$AppointmentListResponseImpl>
    implements _$$AppointmentListResponseImplCopyWith<$Res> {
  __$$AppointmentListResponseImplCopyWithImpl(
      _$AppointmentListResponseImpl _value,
      $Res Function(_$AppointmentListResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? currentPage = null,
    Object? totalPages = null,
  }) {
    return _then(_$AppointmentListResponseImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<AppointmentModel>,
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
class _$AppointmentListResponseImpl implements _AppointmentListResponse {
  const _$AppointmentListResponseImpl(
      {required final List<AppointmentModel> items,
      required this.total,
      @JsonKey(name: 'page') required this.currentPage,
      @JsonKey(name: 'pages') required this.totalPages})
      : _items = items;

  factory _$AppointmentListResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$AppointmentListResponseImplFromJson(json);

  final List<AppointmentModel> _items;
  @override
  List<AppointmentModel> get items {
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
    return 'AppointmentListResponse(items: $items, total: $total, currentPage: $currentPage, totalPages: $totalPages)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AppointmentListResponseImpl &&
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
  _$$AppointmentListResponseImplCopyWith<_$AppointmentListResponseImpl>
      get copyWith => __$$AppointmentListResponseImplCopyWithImpl<
          _$AppointmentListResponseImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AppointmentListResponseImplToJson(
      this,
    );
  }
}

abstract class _AppointmentListResponse implements AppointmentListResponse {
  const factory _AppointmentListResponse(
          {required final List<AppointmentModel> items,
          required final int total,
          @JsonKey(name: 'page') required final int currentPage,
          @JsonKey(name: 'pages') required final int totalPages}) =
      _$AppointmentListResponseImpl;

  factory _AppointmentListResponse.fromJson(Map<String, dynamic> json) =
      _$AppointmentListResponseImpl.fromJson;

  @override
  List<AppointmentModel> get items;
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
  _$$AppointmentListResponseImplCopyWith<_$AppointmentListResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}

CreateAppointmentRequest _$CreateAppointmentRequestFromJson(
    Map<String, dynamic> json) {
  return _CreateAppointmentRequest.fromJson(json);
}

/// @nodoc
mixin _$CreateAppointmentRequest {
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_id')
  int get dentistId => throw _privateConstructorUsedError;
  @JsonKey(name: 'appointment_date')
  String get appointmentDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_time')
  String get startTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_time')
  String? get endTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'notes')
  String? get notes => throw _privateConstructorUsedError;
  @JsonKey(name: 'procedure_type')
  String? get procedureType => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CreateAppointmentRequestCopyWith<CreateAppointmentRequest> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CreateAppointmentRequestCopyWith<$Res> {
  factory $CreateAppointmentRequestCopyWith(CreateAppointmentRequest value,
          $Res Function(CreateAppointmentRequest) then) =
      _$CreateAppointmentRequestCopyWithImpl<$Res, CreateAppointmentRequest>;
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'appointment_date') String appointmentDate,
      @JsonKey(name: 'start_time') String startTime,
      @JsonKey(name: 'end_time') String? endTime,
      @JsonKey(name: 'notes') String? notes,
      @JsonKey(name: 'procedure_type') String? procedureType});
}

/// @nodoc
class _$CreateAppointmentRequestCopyWithImpl<$Res,
        $Val extends CreateAppointmentRequest>
    implements $CreateAppointmentRequestCopyWith<$Res> {
  _$CreateAppointmentRequestCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? dentistId = null,
    Object? appointmentDate = null,
    Object? startTime = null,
    Object? endTime = freezed,
    Object? notes = freezed,
    Object? procedureType = freezed,
  }) {
    return _then(_value.copyWith(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      dentistId: null == dentistId
          ? _value.dentistId
          : dentistId // ignore: cast_nullable_to_non_nullable
              as int,
      appointmentDate: null == appointmentDate
          ? _value.appointmentDate
          : appointmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as String,
      endTime: freezed == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as String?,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      procedureType: freezed == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CreateAppointmentRequestImplCopyWith<$Res>
    implements $CreateAppointmentRequestCopyWith<$Res> {
  factory _$$CreateAppointmentRequestImplCopyWith(
          _$CreateAppointmentRequestImpl value,
          $Res Function(_$CreateAppointmentRequestImpl) then) =
      __$$CreateAppointmentRequestImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'appointment_date') String appointmentDate,
      @JsonKey(name: 'start_time') String startTime,
      @JsonKey(name: 'end_time') String? endTime,
      @JsonKey(name: 'notes') String? notes,
      @JsonKey(name: 'procedure_type') String? procedureType});
}

/// @nodoc
class __$$CreateAppointmentRequestImplCopyWithImpl<$Res>
    extends _$CreateAppointmentRequestCopyWithImpl<$Res,
        _$CreateAppointmentRequestImpl>
    implements _$$CreateAppointmentRequestImplCopyWith<$Res> {
  __$$CreateAppointmentRequestImplCopyWithImpl(
      _$CreateAppointmentRequestImpl _value,
      $Res Function(_$CreateAppointmentRequestImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? dentistId = null,
    Object? appointmentDate = null,
    Object? startTime = null,
    Object? endTime = freezed,
    Object? notes = freezed,
    Object? procedureType = freezed,
  }) {
    return _then(_$CreateAppointmentRequestImpl(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      dentistId: null == dentistId
          ? _value.dentistId
          : dentistId // ignore: cast_nullable_to_non_nullable
              as int,
      appointmentDate: null == appointmentDate
          ? _value.appointmentDate
          : appointmentDate // ignore: cast_nullable_to_non_nullable
              as String,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as String,
      endTime: freezed == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as String?,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      procedureType: freezed == procedureType
          ? _value.procedureType
          : procedureType // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CreateAppointmentRequestImpl implements _CreateAppointmentRequest {
  const _$CreateAppointmentRequestImpl(
      {@JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'dentist_id') required this.dentistId,
      @JsonKey(name: 'appointment_date') required this.appointmentDate,
      @JsonKey(name: 'start_time') required this.startTime,
      @JsonKey(name: 'end_time') this.endTime,
      @JsonKey(name: 'notes') this.notes,
      @JsonKey(name: 'procedure_type') this.procedureType});

  factory _$CreateAppointmentRequestImpl.fromJson(Map<String, dynamic> json) =>
      _$$CreateAppointmentRequestImplFromJson(json);

  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  @override
  @JsonKey(name: 'dentist_id')
  final int dentistId;
  @override
  @JsonKey(name: 'appointment_date')
  final String appointmentDate;
  @override
  @JsonKey(name: 'start_time')
  final String startTime;
  @override
  @JsonKey(name: 'end_time')
  final String? endTime;
  @override
  @JsonKey(name: 'notes')
  final String? notes;
  @override
  @JsonKey(name: 'procedure_type')
  final String? procedureType;

  @override
  String toString() {
    return 'CreateAppointmentRequest(patientId: $patientId, dentistId: $dentistId, appointmentDate: $appointmentDate, startTime: $startTime, endTime: $endTime, notes: $notes, procedureType: $procedureType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CreateAppointmentRequestImpl &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.dentistId, dentistId) ||
                other.dentistId == dentistId) &&
            (identical(other.appointmentDate, appointmentDate) ||
                other.appointmentDate == appointmentDate) &&
            (identical(other.startTime, startTime) ||
                other.startTime == startTime) &&
            (identical(other.endTime, endTime) || other.endTime == endTime) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.procedureType, procedureType) ||
                other.procedureType == procedureType));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, patientId, dentistId,
      appointmentDate, startTime, endTime, notes, procedureType);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CreateAppointmentRequestImplCopyWith<_$CreateAppointmentRequestImpl>
      get copyWith => __$$CreateAppointmentRequestImplCopyWithImpl<
          _$CreateAppointmentRequestImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CreateAppointmentRequestImplToJson(
      this,
    );
  }
}

abstract class _CreateAppointmentRequest implements CreateAppointmentRequest {
  const factory _CreateAppointmentRequest(
      {@JsonKey(name: 'patient_id') required final int patientId,
      @JsonKey(name: 'dentist_id') required final int dentistId,
      @JsonKey(name: 'appointment_date') required final String appointmentDate,
      @JsonKey(name: 'start_time') required final String startTime,
      @JsonKey(name: 'end_time') final String? endTime,
      @JsonKey(name: 'notes') final String? notes,
      @JsonKey(name: 'procedure_type')
      final String? procedureType}) = _$CreateAppointmentRequestImpl;

  factory _CreateAppointmentRequest.fromJson(Map<String, dynamic> json) =
      _$CreateAppointmentRequestImpl.fromJson;

  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  @JsonKey(name: 'dentist_id')
  int get dentistId;
  @override
  @JsonKey(name: 'appointment_date')
  String get appointmentDate;
  @override
  @JsonKey(name: 'start_time')
  String get startTime;
  @override
  @JsonKey(name: 'end_time')
  String? get endTime;
  @override
  @JsonKey(name: 'notes')
  String? get notes;
  @override
  @JsonKey(name: 'procedure_type')
  String? get procedureType;
  @override
  @JsonKey(ignore: true)
  _$$CreateAppointmentRequestImplCopyWith<_$CreateAppointmentRequestImpl>
      get copyWith => throw _privateConstructorUsedError;
}
