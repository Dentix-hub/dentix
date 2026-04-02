// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'lab_order_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

LabWorkItemModel _$LabWorkItemModelFromJson(Map<String, dynamic> json) {
  return _LabWorkItemModel.fromJson(json);
}

/// @nodoc
mixin _$LabWorkItemModel {
  int get id => throw _privateConstructorUsedError;
  String get workType => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  int get quantity => throw _privateConstructorUsedError;
  String? get shade => throw _privateConstructorUsedError;
  String? get material => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $LabWorkItemModelCopyWith<LabWorkItemModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabWorkItemModelCopyWith<$Res> {
  factory $LabWorkItemModelCopyWith(
          LabWorkItemModel value, $Res Function(LabWorkItemModel) then) =
      _$LabWorkItemModelCopyWithImpl<$Res, LabWorkItemModel>;
  @useResult
  $Res call(
      {int id,
      String workType,
      String? description,
      int quantity,
      String? shade,
      String? material});
}

/// @nodoc
class _$LabWorkItemModelCopyWithImpl<$Res, $Val extends LabWorkItemModel>
    implements $LabWorkItemModelCopyWith<$Res> {
  _$LabWorkItemModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? workType = null,
    Object? description = freezed,
    Object? quantity = null,
    Object? shade = freezed,
    Object? material = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      workType: null == workType
          ? _value.workType
          : workType // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      quantity: null == quantity
          ? _value.quantity
          : quantity // ignore: cast_nullable_to_non_nullable
              as int,
      shade: freezed == shade
          ? _value.shade
          : shade // ignore: cast_nullable_to_non_nullable
              as String?,
      material: freezed == material
          ? _value.material
          : material // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$LabWorkItemModelImplCopyWith<$Res>
    implements $LabWorkItemModelCopyWith<$Res> {
  factory _$$LabWorkItemModelImplCopyWith(_$LabWorkItemModelImpl value,
          $Res Function(_$LabWorkItemModelImpl) then) =
      __$$LabWorkItemModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String workType,
      String? description,
      int quantity,
      String? shade,
      String? material});
}

/// @nodoc
class __$$LabWorkItemModelImplCopyWithImpl<$Res>
    extends _$LabWorkItemModelCopyWithImpl<$Res, _$LabWorkItemModelImpl>
    implements _$$LabWorkItemModelImplCopyWith<$Res> {
  __$$LabWorkItemModelImplCopyWithImpl(_$LabWorkItemModelImpl _value,
      $Res Function(_$LabWorkItemModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? workType = null,
    Object? description = freezed,
    Object? quantity = null,
    Object? shade = freezed,
    Object? material = freezed,
  }) {
    return _then(_$LabWorkItemModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      workType: null == workType
          ? _value.workType
          : workType // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      quantity: null == quantity
          ? _value.quantity
          : quantity // ignore: cast_nullable_to_non_nullable
              as int,
      shade: freezed == shade
          ? _value.shade
          : shade // ignore: cast_nullable_to_non_nullable
              as String?,
      material: freezed == material
          ? _value.material
          : material // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LabWorkItemModelImpl extends _LabWorkItemModel {
  const _$LabWorkItemModelImpl(
      {required this.id,
      required this.workType,
      this.description,
      required this.quantity,
      this.shade,
      this.material})
      : super._();

  factory _$LabWorkItemModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LabWorkItemModelImplFromJson(json);

  @override
  final int id;
  @override
  final String workType;
  @override
  final String? description;
  @override
  final int quantity;
  @override
  final String? shade;
  @override
  final String? material;

  @override
  String toString() {
    return 'LabWorkItemModel(id: $id, workType: $workType, description: $description, quantity: $quantity, shade: $shade, material: $material)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabWorkItemModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.workType, workType) ||
                other.workType == workType) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.quantity, quantity) ||
                other.quantity == quantity) &&
            (identical(other.shade, shade) || other.shade == shade) &&
            (identical(other.material, material) ||
                other.material == material));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType, id, workType, description, quantity, shade, material);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$LabWorkItemModelImplCopyWith<_$LabWorkItemModelImpl> get copyWith =>
      __$$LabWorkItemModelImplCopyWithImpl<_$LabWorkItemModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LabWorkItemModelImplToJson(
      this,
    );
  }
}

abstract class _LabWorkItemModel extends LabWorkItemModel {
  const factory _LabWorkItemModel(
      {required final int id,
      required final String workType,
      final String? description,
      required final int quantity,
      final String? shade,
      final String? material}) = _$LabWorkItemModelImpl;
  const _LabWorkItemModel._() : super._();

  factory _LabWorkItemModel.fromJson(Map<String, dynamic> json) =
      _$LabWorkItemModelImpl.fromJson;

  @override
  int get id;
  @override
  String get workType;
  @override
  String? get description;
  @override
  int get quantity;
  @override
  String? get shade;
  @override
  String? get material;
  @override
  @JsonKey(ignore: true)
  _$$LabWorkItemModelImplCopyWith<_$LabWorkItemModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

LabOrderModel _$LabOrderModelFromJson(Map<String, dynamic> json) {
  return _LabOrderModel.fromJson(json);
}

/// @nodoc
mixin _$LabOrderModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_name')
  String? get patientName => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_id')
  int get dentistId => throw _privateConstructorUsedError;
  @JsonKey(name: 'dentist_name')
  String? get dentistName => throw _privateConstructorUsedError;
  @JsonKey(name: 'lab_name')
  String get labName => throw _privateConstructorUsedError;
  @JsonKey(name: 'order_date')
  String get orderDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'due_date')
  String get dueDate => throw _privateConstructorUsedError;
  List<LabWorkItemModel> get items => throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'received_date')
  String? get receivedDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_cost')
  double? get totalCost => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $LabOrderModelCopyWith<LabOrderModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabOrderModelCopyWith<$Res> {
  factory $LabOrderModelCopyWith(
          LabOrderModel value, $Res Function(LabOrderModel) then) =
      _$LabOrderModelCopyWithImpl<$Res, LabOrderModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'lab_name') String labName,
      @JsonKey(name: 'order_date') String orderDate,
      @JsonKey(name: 'due_date') String dueDate,
      List<LabWorkItemModel> items,
      String? notes,
      String status,
      @JsonKey(name: 'received_date') String? receivedDate,
      @JsonKey(name: 'total_cost') double? totalCost,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$LabOrderModelCopyWithImpl<$Res, $Val extends LabOrderModel>
    implements $LabOrderModelCopyWith<$Res> {
  _$LabOrderModelCopyWithImpl(this._value, this._then);

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
    Object? labName = null,
    Object? orderDate = null,
    Object? dueDate = null,
    Object? items = null,
    Object? notes = freezed,
    Object? status = null,
    Object? receivedDate = freezed,
    Object? totalCost = freezed,
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
      labName: null == labName
          ? _value.labName
          : labName // ignore: cast_nullable_to_non_nullable
              as String,
      orderDate: null == orderDate
          ? _value.orderDate
          : orderDate // ignore: cast_nullable_to_non_nullable
              as String,
      dueDate: null == dueDate
          ? _value.dueDate
          : dueDate // ignore: cast_nullable_to_non_nullable
              as String,
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<LabWorkItemModel>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      receivedDate: freezed == receivedDate
          ? _value.receivedDate
          : receivedDate // ignore: cast_nullable_to_non_nullable
              as String?,
      totalCost: freezed == totalCost
          ? _value.totalCost
          : totalCost // ignore: cast_nullable_to_non_nullable
              as double?,
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
abstract class _$$LabOrderModelImplCopyWith<$Res>
    implements $LabOrderModelCopyWith<$Res> {
  factory _$$LabOrderModelImplCopyWith(
          _$LabOrderModelImpl value, $Res Function(_$LabOrderModelImpl) then) =
      __$$LabOrderModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'dentist_id') int dentistId,
      @JsonKey(name: 'dentist_name') String? dentistName,
      @JsonKey(name: 'lab_name') String labName,
      @JsonKey(name: 'order_date') String orderDate,
      @JsonKey(name: 'due_date') String dueDate,
      List<LabWorkItemModel> items,
      String? notes,
      String status,
      @JsonKey(name: 'received_date') String? receivedDate,
      @JsonKey(name: 'total_cost') double? totalCost,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$LabOrderModelImplCopyWithImpl<$Res>
    extends _$LabOrderModelCopyWithImpl<$Res, _$LabOrderModelImpl>
    implements _$$LabOrderModelImplCopyWith<$Res> {
  __$$LabOrderModelImplCopyWithImpl(
      _$LabOrderModelImpl _value, $Res Function(_$LabOrderModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? patientId = null,
    Object? patientName = freezed,
    Object? dentistId = null,
    Object? dentistName = freezed,
    Object? labName = null,
    Object? orderDate = null,
    Object? dueDate = null,
    Object? items = null,
    Object? notes = freezed,
    Object? status = null,
    Object? receivedDate = freezed,
    Object? totalCost = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$LabOrderModelImpl(
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
      labName: null == labName
          ? _value.labName
          : labName // ignore: cast_nullable_to_non_nullable
              as String,
      orderDate: null == orderDate
          ? _value.orderDate
          : orderDate // ignore: cast_nullable_to_non_nullable
              as String,
      dueDate: null == dueDate
          ? _value.dueDate
          : dueDate // ignore: cast_nullable_to_non_nullable
              as String,
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<LabWorkItemModel>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      receivedDate: freezed == receivedDate
          ? _value.receivedDate
          : receivedDate // ignore: cast_nullable_to_non_nullable
              as String?,
      totalCost: freezed == totalCost
          ? _value.totalCost
          : totalCost // ignore: cast_nullable_to_non_nullable
              as double?,
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
class _$LabOrderModelImpl extends _LabOrderModel {
  const _$LabOrderModelImpl(
      {required this.id,
      @JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'patient_name') this.patientName,
      @JsonKey(name: 'dentist_id') required this.dentistId,
      @JsonKey(name: 'dentist_name') this.dentistName,
      @JsonKey(name: 'lab_name') required this.labName,
      @JsonKey(name: 'order_date') required this.orderDate,
      @JsonKey(name: 'due_date') required this.dueDate,
      required final List<LabWorkItemModel> items,
      this.notes,
      required this.status,
      @JsonKey(name: 'received_date') this.receivedDate,
      @JsonKey(name: 'total_cost') this.totalCost,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt})
      : _items = items,
        super._();

  factory _$LabOrderModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LabOrderModelImplFromJson(json);

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
  @JsonKey(name: 'lab_name')
  final String labName;
  @override
  @JsonKey(name: 'order_date')
  final String orderDate;
  @override
  @JsonKey(name: 'due_date')
  final String dueDate;
  final List<LabWorkItemModel> _items;
  @override
  List<LabWorkItemModel> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final String? notes;
  @override
  final String status;
  @override
  @JsonKey(name: 'received_date')
  final String? receivedDate;
  @override
  @JsonKey(name: 'total_cost')
  final double? totalCost;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'LabOrderModel(id: $id, patientId: $patientId, patientName: $patientName, dentistId: $dentistId, dentistName: $dentistName, labName: $labName, orderDate: $orderDate, dueDate: $dueDate, items: $items, notes: $notes, status: $status, receivedDate: $receivedDate, totalCost: $totalCost, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabOrderModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.patientName, patientName) ||
                other.patientName == patientName) &&
            (identical(other.dentistId, dentistId) ||
                other.dentistId == dentistId) &&
            (identical(other.dentistName, dentistName) ||
                other.dentistName == dentistName) &&
            (identical(other.labName, labName) || other.labName == labName) &&
            (identical(other.orderDate, orderDate) ||
                other.orderDate == orderDate) &&
            (identical(other.dueDate, dueDate) || other.dueDate == dueDate) &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.receivedDate, receivedDate) ||
                other.receivedDate == receivedDate) &&
            (identical(other.totalCost, totalCost) ||
                other.totalCost == totalCost) &&
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
      labName,
      orderDate,
      dueDate,
      const DeepCollectionEquality().hash(_items),
      notes,
      status,
      receivedDate,
      totalCost,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$LabOrderModelImplCopyWith<_$LabOrderModelImpl> get copyWith =>
      __$$LabOrderModelImplCopyWithImpl<_$LabOrderModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LabOrderModelImplToJson(
      this,
    );
  }
}

abstract class _LabOrderModel extends LabOrderModel {
  const factory _LabOrderModel(
          {required final int id,
          @JsonKey(name: 'patient_id') required final int patientId,
          @JsonKey(name: 'patient_name') final String? patientName,
          @JsonKey(name: 'dentist_id') required final int dentistId,
          @JsonKey(name: 'dentist_name') final String? dentistName,
          @JsonKey(name: 'lab_name') required final String labName,
          @JsonKey(name: 'order_date') required final String orderDate,
          @JsonKey(name: 'due_date') required final String dueDate,
          required final List<LabWorkItemModel> items,
          final String? notes,
          required final String status,
          @JsonKey(name: 'received_date') final String? receivedDate,
          @JsonKey(name: 'total_cost') final double? totalCost,
          @JsonKey(name: 'created_at') final String? createdAt,
          @JsonKey(name: 'updated_at') final String? updatedAt}) =
      _$LabOrderModelImpl;
  const _LabOrderModel._() : super._();

  factory _LabOrderModel.fromJson(Map<String, dynamic> json) =
      _$LabOrderModelImpl.fromJson;

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
  @JsonKey(name: 'lab_name')
  String get labName;
  @override
  @JsonKey(name: 'order_date')
  String get orderDate;
  @override
  @JsonKey(name: 'due_date')
  String get dueDate;
  @override
  List<LabWorkItemModel> get items;
  @override
  String? get notes;
  @override
  String get status;
  @override
  @JsonKey(name: 'received_date')
  String? get receivedDate;
  @override
  @JsonKey(name: 'total_cost')
  double? get totalCost;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$LabOrderModelImplCopyWith<_$LabOrderModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

LabOrderListResponseModel _$LabOrderListResponseModelFromJson(
    Map<String, dynamic> json) {
  return _LabOrderListResponseModel.fromJson(json);
}

/// @nodoc
mixin _$LabOrderListResponseModel {
  List<LabOrderModel> get items => throw _privateConstructorUsedError;
  @JsonKey(name: 'current_page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_pages')
  int get totalPages => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_items')
  int get totalItems => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $LabOrderListResponseModelCopyWith<LabOrderListResponseModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabOrderListResponseModelCopyWith<$Res> {
  factory $LabOrderListResponseModelCopyWith(LabOrderListResponseModel value,
          $Res Function(LabOrderListResponseModel) then) =
      _$LabOrderListResponseModelCopyWithImpl<$Res, LabOrderListResponseModel>;
  @useResult
  $Res call(
      {List<LabOrderModel> items,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class _$LabOrderListResponseModelCopyWithImpl<$Res,
        $Val extends LabOrderListResponseModel>
    implements $LabOrderListResponseModelCopyWith<$Res> {
  _$LabOrderListResponseModelCopyWithImpl(this._value, this._then);

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
              as List<LabOrderModel>,
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
abstract class _$$LabOrderListResponseModelImplCopyWith<$Res>
    implements $LabOrderListResponseModelCopyWith<$Res> {
  factory _$$LabOrderListResponseModelImplCopyWith(
          _$LabOrderListResponseModelImpl value,
          $Res Function(_$LabOrderListResponseModelImpl) then) =
      __$$LabOrderListResponseModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<LabOrderModel> items,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class __$$LabOrderListResponseModelImplCopyWithImpl<$Res>
    extends _$LabOrderListResponseModelCopyWithImpl<$Res,
        _$LabOrderListResponseModelImpl>
    implements _$$LabOrderListResponseModelImplCopyWith<$Res> {
  __$$LabOrderListResponseModelImplCopyWithImpl(
      _$LabOrderListResponseModelImpl _value,
      $Res Function(_$LabOrderListResponseModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_$LabOrderListResponseModelImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<LabOrderModel>,
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
class _$LabOrderListResponseModelImpl extends _LabOrderListResponseModel {
  const _$LabOrderListResponseModelImpl(
      {required final List<LabOrderModel> items,
      @JsonKey(name: 'current_page') required this.currentPage,
      @JsonKey(name: 'total_pages') required this.totalPages,
      @JsonKey(name: 'total_items') required this.totalItems})
      : _items = items,
        super._();

  factory _$LabOrderListResponseModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LabOrderListResponseModelImplFromJson(json);

  final List<LabOrderModel> _items;
  @override
  List<LabOrderModel> get items {
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
    return 'LabOrderListResponseModel(items: $items, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabOrderListResponseModelImpl &&
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
  _$$LabOrderListResponseModelImplCopyWith<_$LabOrderListResponseModelImpl>
      get copyWith => __$$LabOrderListResponseModelImplCopyWithImpl<
          _$LabOrderListResponseModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LabOrderListResponseModelImplToJson(
      this,
    );
  }
}

abstract class _LabOrderListResponseModel extends LabOrderListResponseModel {
  const factory _LabOrderListResponseModel(
          {required final List<LabOrderModel> items,
          @JsonKey(name: 'current_page') required final int currentPage,
          @JsonKey(name: 'total_pages') required final int totalPages,
          @JsonKey(name: 'total_items') required final int totalItems}) =
      _$LabOrderListResponseModelImpl;
  const _LabOrderListResponseModel._() : super._();

  factory _LabOrderListResponseModel.fromJson(Map<String, dynamic> json) =
      _$LabOrderListResponseModelImpl.fromJson;

  @override
  List<LabOrderModel> get items;
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
  _$$LabOrderListResponseModelImplCopyWith<_$LabOrderListResponseModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

CreateLabOrderRequestModel _$CreateLabOrderRequestModelFromJson(
    Map<String, dynamic> json) {
  return _CreateLabOrderRequestModel.fromJson(json);
}

/// @nodoc
mixin _$CreateLabOrderRequestModel {
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'lab_name')
  String get labName => throw _privateConstructorUsedError;
  @JsonKey(name: 'due_date')
  String get dueDate => throw _privateConstructorUsedError;
  List<Map<String, dynamic>> get items => throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CreateLabOrderRequestModelCopyWith<CreateLabOrderRequestModel>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CreateLabOrderRequestModelCopyWith<$Res> {
  factory $CreateLabOrderRequestModelCopyWith(CreateLabOrderRequestModel value,
          $Res Function(CreateLabOrderRequestModel) then) =
      _$CreateLabOrderRequestModelCopyWithImpl<$Res,
          CreateLabOrderRequestModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'lab_name') String labName,
      @JsonKey(name: 'due_date') String dueDate,
      List<Map<String, dynamic>> items,
      String? notes});
}

/// @nodoc
class _$CreateLabOrderRequestModelCopyWithImpl<$Res,
        $Val extends CreateLabOrderRequestModel>
    implements $CreateLabOrderRequestModelCopyWith<$Res> {
  _$CreateLabOrderRequestModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? labName = null,
    Object? dueDate = null,
    Object? items = null,
    Object? notes = freezed,
  }) {
    return _then(_value.copyWith(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      labName: null == labName
          ? _value.labName
          : labName // ignore: cast_nullable_to_non_nullable
              as String,
      dueDate: null == dueDate
          ? _value.dueDate
          : dueDate // ignore: cast_nullable_to_non_nullable
              as String,
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<Map<String, dynamic>>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CreateLabOrderRequestModelImplCopyWith<$Res>
    implements $CreateLabOrderRequestModelCopyWith<$Res> {
  factory _$$CreateLabOrderRequestModelImplCopyWith(
          _$CreateLabOrderRequestModelImpl value,
          $Res Function(_$CreateLabOrderRequestModelImpl) then) =
      __$$CreateLabOrderRequestModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      @JsonKey(name: 'lab_name') String labName,
      @JsonKey(name: 'due_date') String dueDate,
      List<Map<String, dynamic>> items,
      String? notes});
}

/// @nodoc
class __$$CreateLabOrderRequestModelImplCopyWithImpl<$Res>
    extends _$CreateLabOrderRequestModelCopyWithImpl<$Res,
        _$CreateLabOrderRequestModelImpl>
    implements _$$CreateLabOrderRequestModelImplCopyWith<$Res> {
  __$$CreateLabOrderRequestModelImplCopyWithImpl(
      _$CreateLabOrderRequestModelImpl _value,
      $Res Function(_$CreateLabOrderRequestModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? labName = null,
    Object? dueDate = null,
    Object? items = null,
    Object? notes = freezed,
  }) {
    return _then(_$CreateLabOrderRequestModelImpl(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
      labName: null == labName
          ? _value.labName
          : labName // ignore: cast_nullable_to_non_nullable
              as String,
      dueDate: null == dueDate
          ? _value.dueDate
          : dueDate // ignore: cast_nullable_to_non_nullable
              as String,
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
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
class _$CreateLabOrderRequestModelImpl extends _CreateLabOrderRequestModel {
  const _$CreateLabOrderRequestModelImpl(
      {@JsonKey(name: 'patient_id') required this.patientId,
      @JsonKey(name: 'lab_name') required this.labName,
      @JsonKey(name: 'due_date') required this.dueDate,
      required final List<Map<String, dynamic>> items,
      this.notes})
      : _items = items,
        super._();

  factory _$CreateLabOrderRequestModelImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$CreateLabOrderRequestModelImplFromJson(json);

  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  @override
  @JsonKey(name: 'lab_name')
  final String labName;
  @override
  @JsonKey(name: 'due_date')
  final String dueDate;
  final List<Map<String, dynamic>> _items;
  @override
  List<Map<String, dynamic>> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final String? notes;

  @override
  String toString() {
    return 'CreateLabOrderRequestModel(patientId: $patientId, labName: $labName, dueDate: $dueDate, items: $items, notes: $notes)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CreateLabOrderRequestModelImpl &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.labName, labName) || other.labName == labName) &&
            (identical(other.dueDate, dueDate) || other.dueDate == dueDate) &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.notes, notes) || other.notes == notes));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, patientId, labName, dueDate,
      const DeepCollectionEquality().hash(_items), notes);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CreateLabOrderRequestModelImplCopyWith<_$CreateLabOrderRequestModelImpl>
      get copyWith => __$$CreateLabOrderRequestModelImplCopyWithImpl<
          _$CreateLabOrderRequestModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CreateLabOrderRequestModelImplToJson(
      this,
    );
  }
}

abstract class _CreateLabOrderRequestModel extends CreateLabOrderRequestModel {
  const factory _CreateLabOrderRequestModel(
      {@JsonKey(name: 'patient_id') required final int patientId,
      @JsonKey(name: 'lab_name') required final String labName,
      @JsonKey(name: 'due_date') required final String dueDate,
      required final List<Map<String, dynamic>> items,
      final String? notes}) = _$CreateLabOrderRequestModelImpl;
  const _CreateLabOrderRequestModel._() : super._();

  factory _CreateLabOrderRequestModel.fromJson(Map<String, dynamic> json) =
      _$CreateLabOrderRequestModelImpl.fromJson;

  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  @JsonKey(name: 'lab_name')
  String get labName;
  @override
  @JsonKey(name: 'due_date')
  String get dueDate;
  @override
  List<Map<String, dynamic>> get items;
  @override
  String? get notes;
  @override
  @JsonKey(ignore: true)
  _$$CreateLabOrderRequestModelImplCopyWith<_$CreateLabOrderRequestModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
