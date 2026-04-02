// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'prescription_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

PrescribedMedicationModel _$PrescribedMedicationModelFromJson(
    Map<String, dynamic> json) {
  return _PrescribedMedicationModel.fromJson(json);
}

/// @nodoc
mixin _$PrescribedMedicationModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'medication_id')
  int get medicationId => throw _privateConstructorUsedError;
  @JsonKey(name: 'medication_name')
  String? get medicationName => throw _privateConstructorUsedError;
  String? get dosage => throw _privateConstructorUsedError;
  String? get frequency => throw _privateConstructorUsedError;
  String? get duration => throw _privateConstructorUsedError;
  String? get instructions => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $PrescribedMedicationModelCopyWith<PrescribedMedicationModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescribedMedicationModelCopyWith<$Res> {
  factory $PrescribedMedicationModelCopyWith(PrescribedMedicationModel value,
          $Res Function(PrescribedMedicationModel) then) =
      _$PrescribedMedicationModelCopyWithImpl<$Res, PrescribedMedicationModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'medication_id') int medicationId,
      @JsonKey(name: 'medication_name') String? medicationName,
      String? dosage,
      String? frequency,
      String? duration,
      String? instructions});
}

/// @nodoc
class _$PrescribedMedicationModelCopyWithImpl<$Res,
        $Val extends PrescribedMedicationModel>
    implements $PrescribedMedicationModelCopyWith<$Res> {
  _$PrescribedMedicationModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? medicationId = null,
    Object? medicationName = freezed,
    Object? dosage = freezed,
    Object? frequency = freezed,
    Object? duration = freezed,
    Object? instructions = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      medicationId: null == medicationId
          ? _value.medicationId
          : medicationId // ignore: cast_nullable_to_non_nullable
              as int,
      medicationName: freezed == medicationName
          ? _value.medicationName
          : medicationName // ignore: cast_nullable_to_non_nullable
              as String?,
      dosage: freezed == dosage
          ? _value.dosage
          : dosage // ignore: cast_nullable_to_non_nullable
              as String?,
      frequency: freezed == frequency
          ? _value.frequency
          : frequency // ignore: cast_nullable_to_non_nullable
              as String?,
      duration: freezed == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as String?,
      instructions: freezed == instructions
          ? _value.instructions
          : instructions // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$PrescribedMedicationModelImplCopyWith<$Res>
    implements $PrescribedMedicationModelCopyWith<$Res> {
  factory _$$PrescribedMedicationModelImplCopyWith(
          _$PrescribedMedicationModelImpl value,
          $Res Function(_$PrescribedMedicationModelImpl) then) =
      __$$PrescribedMedicationModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'medication_id') int medicationId,
      @JsonKey(name: 'medication_name') String? medicationName,
      String? dosage,
      String? frequency,
      String? duration,
      String? instructions});
}

/// @nodoc
class __$$PrescribedMedicationModelImplCopyWithImpl<$Res>
    extends _$PrescribedMedicationModelCopyWithImpl<$Res,
        _$PrescribedMedicationModelImpl>
    implements _$$PrescribedMedicationModelImplCopyWith<$Res> {
  __$$PrescribedMedicationModelImplCopyWithImpl(
      _$PrescribedMedicationModelImpl _value,
      $Res Function(_$PrescribedMedicationModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? medicationId = null,
    Object? medicationName = freezed,
    Object? dosage = freezed,
    Object? frequency = freezed,
    Object? duration = freezed,
    Object? instructions = freezed,
  }) {
    return _then(_$PrescribedMedicationModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      medicationId: null == medicationId
          ? _value.medicationId
          : medicationId // ignore: cast_nullable_to_non_nullable
              as int,
      medicationName: freezed == medicationName
          ? _value.medicationName
          : medicationName // ignore: cast_nullable_to_non_nullable
              as String?,
      dosage: freezed == dosage
          ? _value.dosage
          : dosage // ignore: cast_nullable_to_non_nullable
              as String?,
      frequency: freezed == frequency
          ? _value.frequency
          : frequency // ignore: cast_nullable_to_non_nullable
              as String?,
      duration: freezed == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as String?,
      instructions: freezed == instructions
          ? _value.instructions
          : instructions // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$PrescribedMedicationModelImpl extends _PrescribedMedicationModel {
  const _$PrescribedMedicationModelImpl(
      {required this.id,
      @JsonKey(name: 'medication_id') required this.medicationId,
      @JsonKey(name: 'medication_name') this.medicationName,
      this.dosage,
      this.frequency,
      this.duration,
      this.instructions})
      : super._();

  factory _$PrescribedMedicationModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$PrescribedMedicationModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'medication_id')
  final int medicationId;
  @override
  @JsonKey(name: 'medication_name')
  final String? medicationName;
  @override
  final String? dosage;
  @override
  final String? frequency;
  @override
  final String? duration;
  @override
  final String? instructions;

  @override
  String toString() {
    return 'PrescribedMedicationModel(id: $id, medicationId: $medicationId, medicationName: $medicationName, dosage: $dosage, frequency: $frequency, duration: $duration, instructions: $instructions)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescribedMedicationModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.medicationId, medicationId) ||
                other.medicationId == medicationId) &&
            (identical(other.medicationName, medicationName) ||
                other.medicationName == medicationName) &&
            (identical(other.dosage, dosage) || other.dosage == dosage) &&
            (identical(other.frequency, frequency) ||
                other.frequency == frequency) &&
            (identical(other.duration, duration) ||
                other.duration == duration) &&
            (identical(other.instructions, instructions) ||
                other.instructions == instructions));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, id, medicationId, medicationName,
      dosage, frequency, duration, instructions);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PrescribedMedicationModelImplCopyWith<_$PrescribedMedicationModelImpl>
      get copyWith => __$$PrescribedMedicationModelImplCopyWithImpl<
          _$PrescribedMedicationModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PrescribedMedicationModelImplToJson(
      this,
    );
  }
}

abstract class _PrescribedMedicationModel extends PrescribedMedicationModel {
  const factory _PrescribedMedicationModel(
      {required final int id,
      @JsonKey(name: 'medication_id') required final int medicationId,
      @JsonKey(name: 'medication_name') final String? medicationName,
      final String? dosage,
      final String? frequency,
      final String? duration,
      final String? instructions}) = _$PrescribedMedicationModelImpl;
  const _PrescribedMedicationModel._() : super._();

  factory _PrescribedMedicationModel.fromJson(Map<String, dynamic> json) =
      _$PrescribedMedicationModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'medication_id')
  int get medicationId;
  @override
  @JsonKey(name: 'medication_name')
  String? get medicationName;
  @override
  String? get dosage;
  @override
  String? get frequency;
  @override
  String? get duration;
  @override
  String? get instructions;
  @override
  @JsonKey(ignore: true)
  _$$PrescribedMedicationModelImplCopyWith<_$PrescribedMedicationModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

PrescriptionModel _$PrescriptionModelFromJson(Map<String, dynamic> json) {
  return _PrescriptionModel.fromJson(json);
}

/// @nodoc
mixin _$PrescriptionModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_name')
  String? get patientName => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_id')
  int get dentistId => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_name')
  String? get dentistName => throw _privateConstructorUsedError;
  @JsonKey(name: 'prescription_date')
  String get prescriptionDate => throw _privateConstructorUsedError;
  List<PrescribedMedicationModel> get medications =>
      throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  String? get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $PrescriptionModelCopyWith<PrescriptionModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescriptionModelCopyWith<$Res> {
  factory $PrescriptionModelCopyWith(
          PrescriptionModel value, $Res Function(PrescriptionModel) then) =
      _$PrescriptionModelCopyWithImpl<$Res, PrescriptionModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'prescription_date') String prescriptionDate,
      List<PrescribedMedicationModel> medications,
      String? notes,
      String? status,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$PrescriptionModelCopyWithImpl<$Res, $Val extends PrescriptionModel>
    implements $PrescriptionModelCopyWith<$Res> {
  _$PrescriptionModelCopyWithImpl(this._value, this._then);

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
    Object? prescriptionDate = null,
    Object? medications = null,
    Object? notes = freezed,
    Object? status = freezed,
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
      prescriptionDate: null == prescriptionDate
          ? _value.prescriptionDate
          : prescriptionDate // ignore: cast_nullable_to_non_nullable
              as String,
      medications: null == medications
          ? _value.medications
          : medications // ignore: cast_nullable_to_non_nullable
              as List<PrescribedMedicationModel>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: freezed == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
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
abstract class _$$PrescriptionModelImplCopyWith<$Res>
    implements $PrescriptionModelCopyWith<$Res> {
  factory _$$PrescriptionModelImplCopyWith(_$PrescriptionModelImpl value,
          $Res Function(_$PrescriptionModelImpl) then) =
      __$$PrescriptionModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'prescription_date') String prescriptionDate,
      List<PrescribedMedicationModel> medications,
      String? notes,
      String? status,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$PrescriptionModelImplCopyWithImpl<$Res>
    extends _$PrescriptionModelCopyWithImpl<$Res, _$PrescriptionModelImpl>
    implements _$$PrescriptionModelImplCopyWith<$Res> {
  __$$PrescriptionModelImplCopyWithImpl(_$PrescriptionModelImpl _value,
      $Res Function(_$PrescriptionModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? patientName = freezed,
    Object? dentistId = null,
    Object? dentistName = freezed,
    Object? prescriptionDate = null,
    Object? medications = null,
    Object? notes = freezed,
    Object? status = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$PrescriptionModelImpl(
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
      prescriptionDate: null == prescriptionDate
          ? _value.prescriptionDate
          : prescriptionDate // ignore: cast_nullable_to_non_nullable
              as String,
      medications: null == medications
          ? _value._medications
          : medications // ignore: cast_nullable_to_non_nullable
              as List<PrescribedMedicationModel>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: freezed == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
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
class _$PrescriptionModelImpl extends _PrescriptionModel {
  const _$PrescriptionModelImpl(
      {required this.id,
      @JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'patient_name') this.patientName,
      @JsonKey(name: 'dentist_id') required this.dentistId,
      @JsonKey(name: 'dentist_name') this.dentistName,
      @JsonKey(name: 'prescription_date') required this.prescriptionDate,
      required final List<PrescribedMedicationModel> medications,
      this.notes,
      this.status,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt})
      : _medications = medications,
        super._();

  factory _$PrescriptionModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$PrescriptionModelImplFromJson(json);

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
  @JsonKey(name: 'prescription_date')
  final String prescriptionDate;
  final List<PrescribedMedicationModel> _medications;
  @override
  List<PrescribedMedicationModel> get medications {
    if (_medications is EqualUnmodifiableListView) return _medications;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_medications);
  }

  @override
  final String? notes;
  @override
  final String? status;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'PrescriptionModel(id: $id, patientId: $patientId, patientName: $patientName, dentistId: $dentistId, dentistName: $dentistName, prescriptionDate: $prescriptionDate, medications: $medications, notes: $notes, status: $status, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescriptionModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.patientName, patientName) ||
                other.patientName == patientName) &&
            (identical(other.dentistId, dentistId) ||
                other.dentistId == dentistId) &&
            (identical(other.dentistName, dentistName) ||
                other.dentistName == dentistName) &&
            (identical(other.prescriptionDate, prescriptionDate) ||
                other.prescriptionDate == prescriptionDate) &&
            const DeepCollectionEquality()
                .equals(other._medications, _medications) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.status, status) || other.status == status) &&
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
      prescriptionDate,
      const DeepCollectionEquality().hash(_medications),
      notes,
      status,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PrescriptionModelImplCopyWith<_$PrescriptionModelImpl> get copyWith =>
      __$$PrescriptionModelImplCopyWithImpl<_$PrescriptionModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PrescriptionModelImplToJson(
      this,
    );
  }
}

abstract class _PrescriptionModel extends PrescriptionModel {
  const factory _PrescriptionModel(
          {required final int id,
          @JsonKey(name: 'patient_id') required final int patientId,
          @JsonKey(name: 'patient_name') final String? patientName,
          @JsonKey(name: 'dentist_id') required final int dentistId,
          @JsonKey(name: 'dentist_name') final String? dentistName,
          @JsonKey(name: 'prescription_date')
          required final String prescriptionDate,
          required final List<PrescribedMedicationModel> medications,
          final String? notes,
          final String? status,
          @JsonKey(name: 'created_at') final String? createdAt,
          @JsonKey(name: 'updated_at') final String? updatedAt}) =
      _$PrescriptionModelImpl;
  const _PrescriptionModel._() : super._();

  factory _PrescriptionModel.fromJson(Map<String, dynamic> json) =
      _$PrescriptionModelImpl.fromJson;

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
  @JsonKey(name: 'prescription_date')
  String get prescriptionDate;
  @override
  List<PrescribedMedicationModel> get medications;
  @override
  String? get notes;
  @override
  String? get status;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$PrescriptionModelImplCopyWith<_$PrescriptionModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PrescriptionListResponseModel _$PrescriptionListResponseModelFromJson(
    Map<String, dynamic> json) {
  return _PrescriptionListResponseModel.fromJson(json);
}

/// @nodoc
mixin _$PrescriptionListResponseModel {
  List<PrescriptionModel> get items => throw _privateConstructorUsedError;
  @JsonKey(name: 'current_page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_pages')
  int get totalPages => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_items')
  int get totalItems => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $PrescriptionListResponseModelCopyWith<PrescriptionListResponseModel>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescriptionListResponseModelCopyWith<$Res> {
  factory $PrescriptionListResponseModelCopyWith(
          PrescriptionListResponseModel value,
          $Res Function(PrescriptionListResponseModel) then) =
      _$PrescriptionListResponseModelCopyWithImpl<$Res,
          PrescriptionListResponseModel>;
  @useResult
  $Res call(
      {List<PrescriptionModel> items,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class _$PrescriptionListResponseModelCopyWithImpl<$Res,
        $Val extends PrescriptionListResponseModel>
    implements $PrescriptionListResponseModelCopyWith<$Res> {
  _$PrescriptionListResponseModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_value.copyWith(
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<PrescriptionModel>,
      currentPage: null == currentPage
          ? _value.currentPage
          : currentPage // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
      totalItems: null == totalItems
          ? _value.totalItems
          : totalItems // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$PrescriptionListResponseModelImplCopyWith<$Res>
    implements $PrescriptionListResponseModelCopyWith<$Res> {
  factory _$$PrescriptionListResponseModelImplCopyWith(
          _$PrescriptionListResponseModelImpl value,
          $Res Function(_$PrescriptionListResponseModelImpl) then) =
      __$$PrescriptionListResponseModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<PrescriptionModel> items,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class __$$PrescriptionListResponseModelImplCopyWithImpl<$Res>
    extends _$PrescriptionListResponseModelCopyWithImpl<$Res,
        _$PrescriptionListResponseModelImpl>
    implements _$$PrescriptionListResponseModelImplCopyWith<$Res> {
  __$$PrescriptionListResponseModelImplCopyWithImpl(
      _$PrescriptionListResponseModelImpl _value,
      $Res Function(_$PrescriptionListResponseModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_$PrescriptionListResponseModelImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<PrescriptionModel>,
      currentPage: null == currentPage
          ? _value.currentPage
          : currentPage // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
      totalItems: null == totalItems
          ? _value.totalItems
          : totalItems // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$PrescriptionListResponseModelImpl
    extends _PrescriptionListResponseModel {
  const _$PrescriptionListResponseModelImpl(
      {required final List<PrescriptionModel> items,
      @JsonKey(name: 'current_page') required this.currentPage,
      @JsonKey(name: 'total_pages') required this.totalPages,
      @JsonKey(name: 'total_items') required this.totalItems})
      : _items = items,
        super._();

  factory _$PrescriptionListResponseModelImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$PrescriptionListResponseModelImplFromJson(json);

  final List<PrescriptionModel> _items;
  @override
  List<PrescriptionModel> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  @JsonKey(name: 'current_page')
  final int currentPage;
  @override
  @JsonKey(name: 'total_pages')
  final int totalPages;
  @override
  @JsonKey(name: 'total_items')
  final int totalItems;

  @override
  String toString() {
    return 'PrescriptionListResponseModel(items: $items, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescriptionListResponseModelImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.currentPage, currentPage) ||
                other.currentPage == currentPage) &&
            (identical(other.totalPages, totalPages) ||
                other.totalPages == totalPages) &&
            (identical(other.totalItems, totalItems) ||
                other.totalItems == totalItems));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_items),
      currentPage,
      totalPages,
      totalItems);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PrescriptionListResponseModelImplCopyWith<
          _$PrescriptionListResponseModelImpl>
      get copyWith => __$$PrescriptionListResponseModelImplCopyWithImpl<
          _$PrescriptionListResponseModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PrescriptionListResponseModelImplToJson(
      this,
    );
  }
}

abstract class _PrescriptionListResponseModel
    extends PrescriptionListResponseModel {
  const factory _PrescriptionListResponseModel(
          {required final List<PrescriptionModel> items,
          @JsonKey(name: 'current_page') required final int currentPage,
          @JsonKey(name: 'total_pages') required final int totalPages,
          @JsonKey(name: 'total_items') required final int totalItems}) =
      _$PrescriptionListResponseModelImpl;
  const _PrescriptionListResponseModel._() : super._();

  factory _PrescriptionListResponseModel.fromJson(Map<String, dynamic> json) =
      _$PrescriptionListResponseModelImpl.fromJson;

  @override
  List<PrescriptionModel> get items;
  @override
  @JsonKey(name: 'current_page')
  int get currentPage;
  @override
  @JsonKey(name: 'total_pages')
  int get totalPages;
  @override
  @JsonKey(name: 'total_items')
  int get totalItems;
  @override
  @JsonKey(ignore: true)
  _$$PrescriptionListResponseModelImplCopyWith<
          _$PrescriptionListResponseModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

CreatePrescriptionRequestModel _$CreatePrescriptionRequestModelFromJson(
    Map<String, dynamic> json) {
  return _CreatePrescriptionRequestModel.fromJson(json);
}

/// @nodoc
mixin _$CreatePrescriptionRequestModel {
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  List<Map<String, dynamic>> get medications =>
      throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CreatePrescriptionRequestModelCopyWith<CreatePrescriptionRequestModel>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CreatePrescriptionRequestModelCopyWith<$Res> {
  factory $CreatePrescriptionRequestModelCopyWith(
          CreatePrescriptionRequestModel value,
          $Res Function(CreatePrescriptionRequestModel) then) =
      _$CreatePrescriptionRequestModelCopyWithImpl<$Res,
          CreatePrescriptionRequestModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      List<Map<String, dynamic>> medications,
      String? notes});
}

/// @nodoc
class _$CreatePrescriptionRequestModelCopyWithImpl<$Res,
        $Val extends CreatePrescriptionRequestModel>
    implements $CreatePrescriptionRequestModelCopyWith<$Res> {
  _$CreatePrescriptionRequestModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? medications = null,
    Object? notes = freezed,
  }) {
    return _then(_value.copyWith(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      medications: null == medications
          ? _value.medications
          : medications // ignore: cast_nullable_to_non_nullable
              as List<Map<String, dynamic>>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CreatePrescriptionRequestModelImplCopyWith<$Res>
    implements $CreatePrescriptionRequestModelCopyWith<$Res> {
  factory _$$CreatePrescriptionRequestModelImplCopyWith(
          _$CreatePrescriptionRequestModelImpl value,
          $Res Function(_$CreatePrescriptionRequestModelImpl) then) =
      __$$CreatePrescriptionRequestModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      List<Map<String, dynamic>> medications,
      String? notes});
}

/// @nodoc
class __$$CreatePrescriptionRequestModelImplCopyWithImpl<$Res>
    extends _$CreatePrescriptionRequestModelCopyWithImpl<$Res,
        _$CreatePrescriptionRequestModelImpl>
    implements _$$CreatePrescriptionRequestModelImplCopyWith<$Res> {
  __$$CreatePrescriptionRequestModelImplCopyWithImpl(
      _$CreatePrescriptionRequestModelImpl _value,
      $Res Function(_$CreatePrescriptionRequestModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? medications = null,
    Object? notes = freezed,
  }) {
    return _then(_$CreatePrescriptionRequestModelImpl(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      medications: null == medications
          ? _value._medications
          : medications // ignore: cast_nullable_to_non_nullable
              as List<Map<String, dynamic>>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CreatePrescriptionRequestModelImpl
    extends _CreatePrescriptionRequestModel {
  const _$CreatePrescriptionRequestModelImpl(
      {@JsonKey(name: 'patient_id') required this.patientId,
      required final List<Map<String, dynamic>> medications,
      this.notes})
      : _medications = medications,
        super._();

  factory _$CreatePrescriptionRequestModelImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$CreatePrescriptionRequestModelImplFromJson(json);

  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  final List<Map<String, dynamic>> _medications;
  @override
  List<Map<String, dynamic>> get medications {
    if (_medications is EqualUnmodifiableListView) return _medications;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_medications);
  }

  @override
  final String? notes;

  @override
  String toString() {
    return 'CreatePrescriptionRequestModel(patientId: $patientId, medications: $medications, notes: $notes)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CreatePrescriptionRequestModelImpl &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            const DeepCollectionEquality()
                .equals(other._medications, _medications) &&
            (identical(other.notes, notes) || other.notes == notes));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, patientId,
      const DeepCollectionEquality().hash(_medications), notes);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CreatePrescriptionRequestModelImplCopyWith<
          _$CreatePrescriptionRequestModelImpl>
      get copyWith => __$$CreatePrescriptionRequestModelImplCopyWithImpl<
          _$CreatePrescriptionRequestModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CreatePrescriptionRequestModelImplToJson(
      this,
    );
  }
}

abstract class _CreatePrescriptionRequestModel
    extends CreatePrescriptionRequestModel {
  const factory _CreatePrescriptionRequestModel(
      {@JsonKey(name: 'patient_id') required final int patientId,
      required final List<Map<String, dynamic>> medications,
      final String? notes}) = _$CreatePrescriptionRequestModelImpl;
  const _CreatePrescriptionRequestModel._() : super._();

  factory _CreatePrescriptionRequestModel.fromJson(Map<String, dynamic> json) =
      _$CreatePrescriptionRequestModelImpl.fromJson;

  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  List<Map<String, dynamic>> get medications;
  @override
  String? get notes;
  @override
  @JsonKey(ignore: true)
  _$$CreatePrescriptionRequestModelImplCopyWith<
          _$CreatePrescriptionRequestModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
