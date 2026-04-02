// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'lab_order_entity.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$LabOrderEntity {
  int get id => throw _privateConstructorUsedError;
  int get patientId => throw _privateConstructorUsedError;
  String? get patientName => throw _privateConstructorUsedError;
  int get dentistId => throw _privateConstructorUsedError;
  String? get dentistName => throw _privateConstructorUsedError;
  String get labName => throw _privateConstructorUsedError;
  String get orderDate => throw _privateConstructorUsedError;
  String get dueDate => throw _privateConstructorUsedError;
  List<LabWorkItemEntity> get items => throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  LabOrderStatus get status => throw _privateConstructorUsedError;
  String? get receivedDate => throw _privateConstructorUsedError;
  double? get totalCost => throw _privateConstructorUsedError;
  String? get createdAt => throw _privateConstructorUsedError;
  String? get updatedAt => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $LabOrderEntityCopyWith<LabOrderEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabOrderEntityCopyWith<$Res> {
  factory $LabOrderEntityCopyWith(
          LabOrderEntity value, $Res Function(LabOrderEntity) then) =
      _$LabOrderEntityCopyWithImpl<$Res, LabOrderEntity>;
  @useResult
  $Res call(
      {int id,
      int patientId,
      String? patientName,
      int dentistId,
      String? dentistName,
      String labName,
      String orderDate,
      String dueDate,
      List<LabWorkItemEntity> items,
      String? notes,
      LabOrderStatus status,
      String? receivedDate,
      double? totalCost,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class _$LabOrderEntityCopyWithImpl<$Res, $Val extends LabOrderEntity>
    implements $LabOrderEntityCopyWith<$Res> {
  _$LabOrderEntityCopyWithImpl(this._value, this._then);

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
              as List<LabWorkItemEntity>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as LabOrderStatus,
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
abstract class _$$LabOrderEntityImplCopyWith<$Res>
    implements $LabOrderEntityCopyWith<$Res> {
  factory _$$LabOrderEntityImplCopyWith(_$LabOrderEntityImpl value,
          $Res Function(_$LabOrderEntityImpl) then) =
      __$$LabOrderEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      int patientId,
      String? patientName,
      int dentistId,
      String? dentistName,
      String labName,
      String orderDate,
      String dueDate,
      List<LabWorkItemEntity> items,
      String? notes,
      LabOrderStatus status,
      String? receivedDate,
      double? totalCost,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class __$$LabOrderEntityImplCopyWithImpl<$Res>
    extends _$LabOrderEntityCopyWithImpl<$Res, _$LabOrderEntityImpl>
    implements _$$LabOrderEntityImplCopyWith<$Res> {
  __$$LabOrderEntityImplCopyWithImpl(
      _$LabOrderEntityImpl _value, $Res Function(_$LabOrderEntityImpl) _then)
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
    return _then(_$LabOrderEntityImpl(
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
              as List<LabWorkItemEntity>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as LabOrderStatus,
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

class _$LabOrderEntityImpl extends _LabOrderEntity {
  const _$LabOrderEntityImpl(
      {required this.id,
      required this.patientId,
      this.patientName,
      required this.dentistId,
      this.dentistName,
      required this.labName,
      required this.orderDate,
      required this.dueDate,
      required final List<LabWorkItemEntity> items,
      this.notes,
      required this.status,
      this.receivedDate,
      this.totalCost,
      this.createdAt,
      this.updatedAt})
      : _items = items,
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
  final String labName;
  @override
  final String orderDate;
  @override
  final String dueDate;
  final List<LabWorkItemEntity> _items;
  @override
  List<LabWorkItemEntity> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final String? notes;
  @override
  final LabOrderStatus status;
  @override
  final String? receivedDate;
  @override
  final double? totalCost;
  @override
  final String? createdAt;
  @override
  final String? updatedAt;

  @override
  String toString() {
    return 'LabOrderEntity(id: $id, patientId: $patientId, patientName: $patientName, dentistId: $dentistId, dentistName: $dentistName, labName: $labName, orderDate: $orderDate, dueDate: $dueDate, items: $items, notes: $notes, status: $status, receivedDate: $receivedDate, totalCost: $totalCost, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabOrderEntityImpl &&
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
  _$$LabOrderEntityImplCopyWith<_$LabOrderEntityImpl> get copyWith =>
      __$$LabOrderEntityImplCopyWithImpl<_$LabOrderEntityImpl>(
          this, _$identity);
}

abstract class _LabOrderEntity extends LabOrderEntity {
  const factory _LabOrderEntity(
      {required final int id,
      required final int patientId,
      final String? patientName,
      required final int dentistId,
      final String? dentistName,
      required final String labName,
      required final String orderDate,
      required final String dueDate,
      required final List<LabWorkItemEntity> items,
      final String? notes,
      required final LabOrderStatus status,
      final String? receivedDate,
      final double? totalCost,
      final String? createdAt,
      final String? updatedAt}) = _$LabOrderEntityImpl;
  const _LabOrderEntity._() : super._();

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
  String get labName;
  @override
  String get orderDate;
  @override
  String get dueDate;
  @override
  List<LabWorkItemEntity> get items;
  @override
  String? get notes;
  @override
  LabOrderStatus get status;
  @override
  String? get receivedDate;
  @override
  double? get totalCost;
  @override
  String? get createdAt;
  @override
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$LabOrderEntityImplCopyWith<_$LabOrderEntityImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$LabWorkItemEntity {
  int get id => throw _privateConstructorUsedError;
  String get workType => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  int get quantity => throw _privateConstructorUsedError;
  String? get shade => throw _privateConstructorUsedError;
  String? get material => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $LabWorkItemEntityCopyWith<LabWorkItemEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabWorkItemEntityCopyWith<$Res> {
  factory $LabWorkItemEntityCopyWith(
          LabWorkItemEntity value, $Res Function(LabWorkItemEntity) then) =
      _$LabWorkItemEntityCopyWithImpl<$Res, LabWorkItemEntity>;
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
class _$LabWorkItemEntityCopyWithImpl<$Res, $Val extends LabWorkItemEntity>
    implements $LabWorkItemEntityCopyWith<$Res> {
  _$LabWorkItemEntityCopyWithImpl(this._value, this._then);

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
abstract class _$$LabWorkItemEntityImplCopyWith<$Res>
    implements $LabWorkItemEntityCopyWith<$Res> {
  factory _$$LabWorkItemEntityImplCopyWith(_$LabWorkItemEntityImpl value,
          $Res Function(_$LabWorkItemEntityImpl) then) =
      __$$LabWorkItemEntityImplCopyWithImpl<$Res>;
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
class __$$LabWorkItemEntityImplCopyWithImpl<$Res>
    extends _$LabWorkItemEntityCopyWithImpl<$Res, _$LabWorkItemEntityImpl>
    implements _$$LabWorkItemEntityImplCopyWith<$Res> {
  __$$LabWorkItemEntityImplCopyWithImpl(_$LabWorkItemEntityImpl _value,
      $Res Function(_$LabWorkItemEntityImpl) _then)
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
    return _then(_$LabWorkItemEntityImpl(
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

class _$LabWorkItemEntityImpl extends _LabWorkItemEntity {
  const _$LabWorkItemEntityImpl(
      {required this.id,
      required this.workType,
      this.description,
      required this.quantity,
      this.shade,
      this.material})
      : super._();

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
    return 'LabWorkItemEntity(id: $id, workType: $workType, description: $description, quantity: $quantity, shade: $shade, material: $material)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabWorkItemEntityImpl &&
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

  @override
  int get hashCode => Object.hash(
      runtimeType, id, workType, description, quantity, shade, material);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$LabWorkItemEntityImplCopyWith<_$LabWorkItemEntityImpl> get copyWith =>
      __$$LabWorkItemEntityImplCopyWithImpl<_$LabWorkItemEntityImpl>(
          this, _$identity);
}

abstract class _LabWorkItemEntity extends LabWorkItemEntity {
  const factory _LabWorkItemEntity(
      {required final int id,
      required final String workType,
      final String? description,
      required final int quantity,
      final String? shade,
      final String? material}) = _$LabWorkItemEntityImpl;
  const _LabWorkItemEntity._() : super._();

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
  _$$LabWorkItemEntityImplCopyWith<_$LabWorkItemEntityImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$LabOrderListEntity {
  List<LabOrderEntity> get items => throw _privateConstructorUsedError;
  int get currentPage => throw _privateConstructorUsedError;
  int get totalPages => throw _privateConstructorUsedError;
  int get totalItems => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $LabOrderListEntityCopyWith<LabOrderListEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LabOrderListEntityCopyWith<$Res> {
  factory $LabOrderListEntityCopyWith(
          LabOrderListEntity value, $Res Function(LabOrderListEntity) then) =
      _$LabOrderListEntityCopyWithImpl<$Res, LabOrderListEntity>;
  @useResult
  $Res call(
      {List<LabOrderEntity> items,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class _$LabOrderListEntityCopyWithImpl<$Res, $Val extends LabOrderListEntity>
    implements $LabOrderListEntityCopyWith<$Res> {
  _$LabOrderListEntityCopyWithImpl(this._value, this._then);

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
              as List<LabOrderEntity>,
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
abstract class _$$LabOrderListEntityImplCopyWith<$Res>
    implements $LabOrderListEntityCopyWith<$Res> {
  factory _$$LabOrderListEntityImplCopyWith(_$LabOrderListEntityImpl value,
          $Res Function(_$LabOrderListEntityImpl) then) =
      __$$LabOrderListEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<LabOrderEntity> items,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class __$$LabOrderListEntityImplCopyWithImpl<$Res>
    extends _$LabOrderListEntityCopyWithImpl<$Res, _$LabOrderListEntityImpl>
    implements _$$LabOrderListEntityImplCopyWith<$Res> {
  __$$LabOrderListEntityImplCopyWithImpl(_$LabOrderListEntityImpl _value,
      $Res Function(_$LabOrderListEntityImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_$LabOrderListEntityImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<LabOrderEntity>,
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

class _$LabOrderListEntityImpl extends _LabOrderListEntity {
  const _$LabOrderListEntityImpl(
      {required final List<LabOrderEntity> items,
      required this.currentPage,
      required this.totalPages,
      required this.totalItems})
      : _items = items,
        super._();

  final List<LabOrderEntity> _items;
  @override
  List<LabOrderEntity> get items {
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
    return 'LabOrderListEntity(items: $items, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LabOrderListEntityImpl &&
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
  _$$LabOrderListEntityImplCopyWith<_$LabOrderListEntityImpl> get copyWith =>
      __$$LabOrderListEntityImplCopyWithImpl<_$LabOrderListEntityImpl>(
          this, _$identity);
}

abstract class _LabOrderListEntity extends LabOrderListEntity {
  const factory _LabOrderListEntity(
      {required final List<LabOrderEntity> items,
      required final int currentPage,
      required final int totalPages,
      required final int totalItems}) = _$LabOrderListEntityImpl;
  const _LabOrderListEntity._() : super._();

  @override
  List<LabOrderEntity> get items;
  @override
  int get currentPage;
  @override
  int get totalPages;
  @override
  int get totalItems;
  @override
  @JsonKey(ignore: true)
  _$$LabOrderListEntityImplCopyWith<_$LabOrderListEntityImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
