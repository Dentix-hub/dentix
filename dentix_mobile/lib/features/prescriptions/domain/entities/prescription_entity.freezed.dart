// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'prescription_entity.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$PrescriptionEntity {
  int get id => throw _privateConstructorUsedError;
  int get patientId => throw _privateConstructorUsedError;
  String? get patientName => throw _privateConstructorUsedError;
  int get dentistId => throw _privateConstructorUsedError;
  String? get dentistName => throw _privateConstructorUsedError;
  String get prescriptionDate => throw _privateConstructorUsedError;
  List<PrescribedMedicationEntity> get medications =>
      throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  String? get status => throw _privateConstructorUsedError;
  String? get createdAt => throw _privateConstructorUsedError;
  String? get updatedAt => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $PrescriptionEntityCopyWith<PrescriptionEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescriptionEntityCopyWith<$Res> {
  factory $PrescriptionEntityCopyWith(
          PrescriptionEntity value, $Res Function(PrescriptionEntity) then) =
      _$PrescriptionEntityCopyWithImpl<$Res, PrescriptionEntity>;
  @useResult
  $Res call(
      {int id,
      int patientId,
      String? patientName,
      int dentistId,
      String? dentistName,
      String prescriptionDate,
      List<PrescribedMedicationEntity> medications,
      String? notes,
      String? status,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class _$PrescriptionEntityCopyWithImpl<$Res, $Val extends PrescriptionEntity>
    implements $PrescriptionEntityCopyWith<$Res> {
  _$PrescriptionEntityCopyWithImpl(this._value, this._then);

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
              as List<PrescribedMedicationEntity>,
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
abstract class _$$PrescriptionEntityImplCopyWith<$Res>
    implements $PrescriptionEntityCopyWith<$Res> {
  factory _$$PrescriptionEntityImplCopyWith(_$PrescriptionEntityImpl value,
          $Res Function(_$PrescriptionEntityImpl) then) =
      __$$PrescriptionEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      int patientId,
      String? patientName,
      int dentistId,
      String? dentistName,
      String prescriptionDate,
      List<PrescribedMedicationEntity> medications,
      String? notes,
      String? status,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class __$$PrescriptionEntityImplCopyWithImpl<$Res>
    extends _$PrescriptionEntityCopyWithImpl<$Res, _$PrescriptionEntityImpl>
    implements _$$PrescriptionEntityImplCopyWith<$Res> {
  __$$PrescriptionEntityImplCopyWithImpl(_$PrescriptionEntityImpl _value,
      $Res Function(_$PrescriptionEntityImpl) _then)
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
    return _then(_$PrescriptionEntityImpl(
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
              as List<PrescribedMedicationEntity>,
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

class _$PrescriptionEntityImpl extends _PrescriptionEntity {
  const _$PrescriptionEntityImpl(
      {required this.id,
      required this.patientId,
      this.patientName,
      required this.dentistId,
      this.dentistName,
      required this.prescriptionDate,
      required final List<PrescribedMedicationEntity> medications,
      this.notes,
      this.status,
      this.createdAt,
      this.updatedAt})
      : _medications = medications,
        super._();

  @override
  final int id;
  @override
  final int patientId;
  @override
  final String? patientName;
  @override
  final int dentistId;
  @override
  final String? dentistName;
  @override
  final String prescriptionDate;
  final List<PrescribedMedicationEntity> _medications;
  @override
  List<PrescribedMedicationEntity> get medications {
    if (_medications is EqualUnmodifiableListView) return _medications;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_medications);
  }

  @override
  final String? notes;
  @override
  final String? status;
  @override
  final String? createdAt;
  @override
  final String? updatedAt;

  @override
  String toString() {
    return 'PrescriptionEntity(id: $id, patientId: $patientId, patientName: $patientName, dentistId: $dentistId, dentistName: $dentistName, prescriptionDate: $prescriptionDate, medications: $medications, notes: $notes, status: $status, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescriptionEntityImpl &&
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
  _$$PrescriptionEntityImplCopyWith<_$PrescriptionEntityImpl> get copyWith =>
      __$$PrescriptionEntityImplCopyWithImpl<_$PrescriptionEntityImpl>(
          this, _$identity);
}

abstract class _PrescriptionEntity extends PrescriptionEntity {
  const factory _PrescriptionEntity(
      {required final int id,
      required final int patientId,
      final String? patientName,
      required final int dentistId,
      final String? dentistName,
      required final String prescriptionDate,
      required final List<PrescribedMedicationEntity> medications,
      final String? notes,
      final String? status,
      final String? createdAt,
      final String? updatedAt}) = _$PrescriptionEntityImpl;
  const _PrescriptionEntity._() : super._();

  @override
  int get id;
  @override
  int get patientId;
  @override
  String? get patientName;
  @override
  int get dentistId;
  @override
  String? get dentistName;
  @override
  String get prescriptionDate;
  @override
  List<PrescribedMedicationEntity> get medications;
  @override
  String? get notes;
  @override
  String? get status;
  @override
  String? get createdAt;
  @override
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$PrescriptionEntityImplCopyWith<_$PrescriptionEntityImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$PrescribedMedicationEntity {
  int get id => throw _privateConstructorUsedError;
  int get medicationId => throw _privateConstructorUsedError;
  String? get medicationName => throw _privateConstructorUsedError;
  String? get dosage => throw _privateConstructorUsedError;
  String? get frequency => throw _privateConstructorUsedError;
  String? get duration => throw _privateConstructorUsedError;
  String? get instructions => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $PrescribedMedicationEntityCopyWith<PrescribedMedicationEntity>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescribedMedicationEntityCopyWith<$Res> {
  factory $PrescribedMedicationEntityCopyWith(PrescribedMedicationEntity value,
          $Res Function(PrescribedMedicationEntity) then) =
      _$PrescribedMedicationEntityCopyWithImpl<$Res,
          PrescribedMedicationEntity>;
  @useResult
  $Res call(
      {int id,
      int medicationId,
      String? medicationName,
      String? dosage,
      String? frequency,
      String? duration,
      String? instructions});
}

/// @nodoc
class _$PrescribedMedicationEntityCopyWithImpl<$Res,
        $Val extends PrescribedMedicationEntity>
    implements $PrescribedMedicationEntityCopyWith<$Res> {
  _$PrescribedMedicationEntityCopyWithImpl(this._value, this._then);

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
abstract class _$$PrescribedMedicationEntityImplCopyWith<$Res>
    implements $PrescribedMedicationEntityCopyWith<$Res> {
  factory _$$PrescribedMedicationEntityImplCopyWith(
          _$PrescribedMedicationEntityImpl value,
          $Res Function(_$PrescribedMedicationEntityImpl) then) =
      __$$PrescribedMedicationEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      int medicationId,
      String? medicationName,
      String? dosage,
      String? frequency,
      String? duration,
      String? instructions});
}

/// @nodoc
class __$$PrescribedMedicationEntityImplCopyWithImpl<$Res>
    extends _$PrescribedMedicationEntityCopyWithImpl<$Res,
        _$PrescribedMedicationEntityImpl>
    implements _$$PrescribedMedicationEntityImplCopyWith<$Res> {
  __$$PrescribedMedicationEntityImplCopyWithImpl(
      _$PrescribedMedicationEntityImpl _value,
      $Res Function(_$PrescribedMedicationEntityImpl) _then)
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
    return _then(_$PrescribedMedicationEntityImpl(
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

class _$PrescribedMedicationEntityImpl extends _PrescribedMedicationEntity {
  const _$PrescribedMedicationEntityImpl(
      {required this.id,
      required this.medicationId,
      this.medicationName,
      this.dosage,
      this.frequency,
      this.duration,
      this.instructions})
      : super._();

  @override
  final int id;
  @override
  final int medicationId;
  @override
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
    return 'PrescribedMedicationEntity(id: $id, medicationId: $medicationId, medicationName: $medicationName, dosage: $dosage, frequency: $frequency, duration: $duration, instructions: $instructions)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescribedMedicationEntityImpl &&
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

  @override
  int get hashCode => Object.hash(runtimeType, id, medicationId, medicationName,
      dosage, frequency, duration, instructions);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PrescribedMedicationEntityImplCopyWith<_$PrescribedMedicationEntityImpl>
      get copyWith => __$$PrescribedMedicationEntityImplCopyWithImpl<
          _$PrescribedMedicationEntityImpl>(this, _$identity);
}

abstract class _PrescribedMedicationEntity extends PrescribedMedicationEntity {
  const factory _PrescribedMedicationEntity(
      {required final int id,
      required final int medicationId,
      final String? medicationName,
      final String? dosage,
      final String? frequency,
      final String? duration,
      final String? instructions}) = _$PrescribedMedicationEntityImpl;
  const _PrescribedMedicationEntity._() : super._();

  @override
  int get id;
  @override
  int get medicationId;
  @override
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
  _$$PrescribedMedicationEntityImplCopyWith<_$PrescribedMedicationEntityImpl>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$PrescriptionListEntity {
  List<PrescriptionEntity> get items => throw _privateConstructorUsedError;
  int get currentPage => throw _privateConstructorUsedError;
  int get totalPages => throw _privateConstructorUsedError;
  int get totalItems => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $PrescriptionListEntityCopyWith<PrescriptionListEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PrescriptionListEntityCopyWith<$Res> {
  factory $PrescriptionListEntityCopyWith(PrescriptionListEntity value,
          $Res Function(PrescriptionListEntity) then) =
      _$PrescriptionListEntityCopyWithImpl<$Res, PrescriptionListEntity>;
  @useResult
  $Res call(
      {List<PrescriptionEntity> items,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class _$PrescriptionListEntityCopyWithImpl<$Res,
        $Val extends PrescriptionListEntity>
    implements $PrescriptionListEntityCopyWith<$Res> {
  _$PrescriptionListEntityCopyWithImpl(this._value, this._then);

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
              as List<PrescriptionEntity>,
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
abstract class _$$PrescriptionListEntityImplCopyWith<$Res>
    implements $PrescriptionListEntityCopyWith<$Res> {
  factory _$$PrescriptionListEntityImplCopyWith(
          _$PrescriptionListEntityImpl value,
          $Res Function(_$PrescriptionListEntityImpl) then) =
      __$$PrescriptionListEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<PrescriptionEntity> items,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class __$$PrescriptionListEntityImplCopyWithImpl<$Res>
    extends _$PrescriptionListEntityCopyWithImpl<$Res,
        _$PrescriptionListEntityImpl>
    implements _$$PrescriptionListEntityImplCopyWith<$Res> {
  __$$PrescriptionListEntityImplCopyWithImpl(
      _$PrescriptionListEntityImpl _value,
      $Res Function(_$PrescriptionListEntityImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_$PrescriptionListEntityImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<PrescriptionEntity>,
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

class _$PrescriptionListEntityImpl extends _PrescriptionListEntity {
  const _$PrescriptionListEntityImpl(
      {required final List<PrescriptionEntity> items,
      required this.currentPage,
      required this.totalPages,
      required this.totalItems})
      : _items = items,
        super._();

  final List<PrescriptionEntity> _items;
  @override
  List<PrescriptionEntity> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final int currentPage;
  @override
  final int totalPages;
  @override
  final int totalItems;

  @override
  String toString() {
    return 'PrescriptionListEntity(items: $items, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PrescriptionListEntityImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.currentPage, currentPage) ||
                other.currentPage == currentPage) &&
            (identical(other.totalPages, totalPages) ||
                other.totalPages == totalPages) &&
            (identical(other.totalItems, totalItems) ||
                other.totalItems == totalItems));
  }

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
  _$$PrescriptionListEntityImplCopyWith<_$PrescriptionListEntityImpl>
      get copyWith => __$$PrescriptionListEntityImplCopyWithImpl<
          _$PrescriptionListEntityImpl>(this, _$identity);
}

abstract class _PrescriptionListEntity extends PrescriptionListEntity {
  const factory _PrescriptionListEntity(
      {required final List<PrescriptionEntity> items,
      required final int currentPage,
      required final int totalPages,
      required final int totalItems}) = _$PrescriptionListEntityImpl;
  const _PrescriptionListEntity._() : super._();

  @override
  List<PrescriptionEntity> get items;
  @override
  int get currentPage;
  @override
  int get totalPages;
  @override
  int get totalItems;
  @override
  @JsonKey(ignore: true)
  _$$PrescriptionListEntityImplCopyWith<_$PrescriptionListEntityImpl>
      get copyWith => throw _privateConstructorUsedError;
}
