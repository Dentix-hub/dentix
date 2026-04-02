// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'financial_transaction_entity.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$FinancialTransactionEntity {
  int get id => throw _privateConstructorUsedError;
  TransactionType get type => throw _privateConstructorUsedError;
  double get amount => throw _privateConstructorUsedError;
  String get date => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  int? get patientId => throw _privateConstructorUsedError;
  String? get patientName => throw _privateConstructorUsedError;
  int? get appointmentId => throw _privateConstructorUsedError;
  int? get treatmentId => throw _privateConstructorUsedError;
  String? get category => throw _privateConstructorUsedError;
  String? get createdAt => throw _privateConstructorUsedError;
  String? get updatedAt => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $FinancialTransactionEntityCopyWith<FinancialTransactionEntity>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FinancialTransactionEntityCopyWith<$Res> {
  factory $FinancialTransactionEntityCopyWith(FinancialTransactionEntity value,
          $Res Function(FinancialTransactionEntity) then) =
      _$FinancialTransactionEntityCopyWithImpl<$Res,
          FinancialTransactionEntity>;
  @useResult
  $Res call(
      {int id,
      TransactionType type,
      double amount,
      String date,
      String? description,
      int? patientId,
      String? patientName,
      int? appointmentId,
      int? treatmentId,
      String? category,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class _$FinancialTransactionEntityCopyWithImpl<$Res,
        $Val extends FinancialTransactionEntity>
    implements $FinancialTransactionEntityCopyWith<$Res> {
  _$FinancialTransactionEntityCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? type = null,
    Object? amount = null,
    Object? date = null,
    Object? description = freezed,
    Object? patientId = freezed,
    Object? patientName = freezed,
    Object? appointmentId = freezed,
    Object? treatmentId = freezed,
    Object? category = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as TransactionType,
      amount: null == amount
          ? _value.amount
          : amount // ignore: cast_nullable_to_non_nullable
              as double,
      date: null == date
          ? _value.date
          : date // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      patientId: freezed == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int?,
      patientName: freezed == patientName
          ? _value.patientName
          : patientName // ignore: cast_nullable_to_non_nullable
              as String?,
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      treatmentId: freezed == treatmentId
          ? _value.treatmentId
          : treatmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      category: freezed == category
          ? _value.category
          : category // ignore: cast_nullable_to_non_nullable
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
abstract class _$$FinancialTransactionEntityImplCopyWith<$Res>
    implements $FinancialTransactionEntityCopyWith<$Res> {
  factory _$$FinancialTransactionEntityImplCopyWith(
          _$FinancialTransactionEntityImpl value,
          $Res Function(_$FinancialTransactionEntityImpl) then) =
      __$$FinancialTransactionEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      TransactionType type,
      double amount,
      String date,
      String? description,
      int? patientId,
      String? patientName,
      int? appointmentId,
      int? treatmentId,
      String? category,
      String? createdAt,
      String? updatedAt});
}

/// @nodoc
class __$$FinancialTransactionEntityImplCopyWithImpl<$Res>
    extends _$FinancialTransactionEntityCopyWithImpl<$Res,
        _$FinancialTransactionEntityImpl>
    implements _$$FinancialTransactionEntityImplCopyWith<$Res> {
  __$$FinancialTransactionEntityImplCopyWithImpl(
      _$FinancialTransactionEntityImpl _value,
      $Res Function(_$FinancialTransactionEntityImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? type = null,
    Object? amount = null,
    Object? date = null,
    Object? description = freezed,
    Object? patientId = freezed,
    Object? patientName = freezed,
    Object? appointmentId = freezed,
    Object? treatmentId = freezed,
    Object? category = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$FinancialTransactionEntityImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as TransactionType,
      amount: null == amount
          ? _value.amount
          : amount // ignore: cast_nullable_to_non_nullable
              as double,
      date: null == date
          ? _value.date
          : date // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      patientId: freezed == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int?,
      patientName: freezed == patientName
          ? _value.patientName
          : patientName // ignore: cast_nullable_to_non_nullable
              as String?,
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      treatmentId: freezed == treatmentId
          ? _value.treatmentId
          : treatmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      category: freezed == category
          ? _value.category
          : category // ignore: cast_nullable_to_non_nullable
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

class _$FinancialTransactionEntityImpl extends _FinancialTransactionEntity {
  const _$FinancialTransactionEntityImpl(
      {required this.id,
      required this.type,
      required this.amount,
      required this.date,
      this.description,
      this.patientId,
      this.patientName,
      this.appointmentId,
      this.treatmentId,
      this.category,
      this.createdAt,
      this.updatedAt})
      : super._();

  @override
  final int id;
  @override
  final TransactionType type;
  @override
  final double amount;
  @override
  final String date;
  @override
  final String? description;
  @override
  final int? patientId;
  @override
  final String? patientName;
  @override
  final int? appointmentId;
  @override
  final int? treatmentId;
  @override
  final String? category;
  @override
  final String? createdAt;
  @override
  final String? updatedAt;

  @override
  String toString() {
    return 'FinancialTransactionEntity(id: $id, type: $type, amount: $amount, date: $date, description: $description, patientId: $patientId, patientName: $patientName, appointmentId: $appointmentId, treatmentId: $treatmentId, category: $category, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FinancialTransactionEntityImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.amount, amount) || other.amount == amount) &&
            (identical(other.date, date) || other.date == date) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.patientName, patientName) ||
                other.patientName == patientName) &&
            (identical(other.appointmentId, appointmentId) ||
                other.appointmentId == appointmentId) &&
            (identical(other.treatmentId, treatmentId) ||
                other.treatmentId == treatmentId) &&
            (identical(other.category, category) ||
                other.category == category) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.updatedAt, updatedAt) ||
                other.updatedAt == updatedAt));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      type,
      amount,
      date,
      description,
      patientId,
      patientName,
      appointmentId,
      treatmentId,
      category,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FinancialTransactionEntityImplCopyWith<_$FinancialTransactionEntityImpl>
      get copyWith => __$$FinancialTransactionEntityImplCopyWithImpl<
          _$FinancialTransactionEntityImpl>(this, _$identity);
}

abstract class _FinancialTransactionEntity extends FinancialTransactionEntity {
  const factory _FinancialTransactionEntity(
      {required final int id,
      required final TransactionType type,
      required final double amount,
      required final String date,
      final String? description,
      final int? patientId,
      final String? patientName,
      final int? appointmentId,
      final int? treatmentId,
      final String? category,
      final String? createdAt,
      final String? updatedAt}) = _$FinancialTransactionEntityImpl;
  const _FinancialTransactionEntity._() : super._();

  @override
  int get id;
  @override
  TransactionType get type;
  @override
  double get amount;
  @override
  String get date;
  @override
  String? get description;
  @override
  int? get patientId;
  @override
  String? get patientName;
  @override
  int? get appointmentId;
  @override
  int? get treatmentId;
  @override
  String? get category;
  @override
  String? get createdAt;
  @override
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$FinancialTransactionEntityImplCopyWith<_$FinancialTransactionEntityImpl>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$FinancialOverviewEntity {
  List<FinancialTransactionEntity> get items =>
      throw _privateConstructorUsedError;
  int get totalRevenue => throw _privateConstructorUsedError;
  int get totalExpenses => throw _privateConstructorUsedError;
  double get netIncome => throw _privateConstructorUsedError;
  int get currentPage => throw _privateConstructorUsedError;
  int get totalPages => throw _privateConstructorUsedError;
  int get totalItems => throw _privateConstructorUsedError;

  @JsonKey(ignore: true)
  $FinancialOverviewEntityCopyWith<FinancialOverviewEntity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FinancialOverviewEntityCopyWith<$Res> {
  factory $FinancialOverviewEntityCopyWith(FinancialOverviewEntity value,
          $Res Function(FinancialOverviewEntity) then) =
      _$FinancialOverviewEntityCopyWithImpl<$Res, FinancialOverviewEntity>;
  @useResult
  $Res call(
      {List<FinancialTransactionEntity> items,
      int totalRevenue,
      int totalExpenses,
      double netIncome,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class _$FinancialOverviewEntityCopyWithImpl<$Res,
        $Val extends FinancialOverviewEntity>
    implements $FinancialOverviewEntityCopyWith<$Res> {
  _$FinancialOverviewEntityCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? totalRevenue = null,
    Object? totalExpenses = null,
    Object? netIncome = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_value.copyWith(
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<FinancialTransactionEntity>,
      totalRevenue: null == totalRevenue
          ? _value.totalRevenue
          : totalRevenue // ignore: cast_nullable_to_non_nullable
              as int,
      totalExpenses: null == totalExpenses
          ? _value.totalExpenses
          : totalExpenses // ignore: cast_nullable_to_non_nullable
              as int,
      netIncome: null == netIncome
          ? _value.netIncome
          : netIncome // ignore: cast_nullable_to_non_nullable
              as double,
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
abstract class _$$FinancialOverviewEntityImplCopyWith<$Res>
    implements $FinancialOverviewEntityCopyWith<$Res> {
  factory _$$FinancialOverviewEntityImplCopyWith(
          _$FinancialOverviewEntityImpl value,
          $Res Function(_$FinancialOverviewEntityImpl) then) =
      __$$FinancialOverviewEntityImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<FinancialTransactionEntity> items,
      int totalRevenue,
      int totalExpenses,
      double netIncome,
      int currentPage,
      int totalPages,
      int totalItems});
}

/// @nodoc
class __$$FinancialOverviewEntityImplCopyWithImpl<$Res>
    extends _$FinancialOverviewEntityCopyWithImpl<$Res,
        _$FinancialOverviewEntityImpl>
    implements _$$FinancialOverviewEntityImplCopyWith<$Res> {
  __$$FinancialOverviewEntityImplCopyWithImpl(
      _$FinancialOverviewEntityImpl _value,
      $Res Function(_$FinancialOverviewEntityImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? totalRevenue = null,
    Object? totalExpenses = null,
    Object? netIncome = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? totalItems = null,
  }) {
    return _then(_$FinancialOverviewEntityImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<FinancialTransactionEntity>,
      totalRevenue: null == totalRevenue
          ? _value.totalRevenue
          : totalRevenue // ignore: cast_nullable_to_non_nullable
              as int,
      totalExpenses: null == totalExpenses
          ? _value.totalExpenses
          : totalExpenses // ignore: cast_nullable_to_non_nullable
              as int,
      netIncome: null == netIncome
          ? _value.netIncome
          : netIncome // ignore: cast_nullable_to_non_nullable
              as double,
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

class _$FinancialOverviewEntityImpl extends _FinancialOverviewEntity {
  const _$FinancialOverviewEntityImpl(
      {required final List<FinancialTransactionEntity> items,
      required this.totalRevenue,
      required this.totalExpenses,
      required this.netIncome,
      required this.currentPage,
      required this.totalPages,
      required this.totalItems})
      : _items = items,
        super._();

  final List<FinancialTransactionEntity> _items;
  @override
  List<FinancialTransactionEntity> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final int totalRevenue;
  @override
  final int totalExpenses;
  @override
  final double netIncome;
  @override
  final int currentPage;
  @override
  final int totalPages;
  @override
  final int totalItems;

  @override
  String toString() {
    return 'FinancialOverviewEntity(items: $items, totalRevenue: $totalRevenue, totalExpenses: $totalExpenses, netIncome: $netIncome, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FinancialOverviewEntityImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.totalRevenue, totalRevenue) ||
                other.totalRevenue == totalRevenue) &&
            (identical(other.totalExpenses, totalExpenses) ||
                other.totalExpenses == totalExpenses) &&
            (identical(other.netIncome, netIncome) ||
                other.netIncome == netIncome) &&
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
      totalRevenue,
      totalExpenses,
      netIncome,
      currentPage,
      totalPages,
      totalItems);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FinancialOverviewEntityImplCopyWith<_$FinancialOverviewEntityImpl>
      get copyWith => __$$FinancialOverviewEntityImplCopyWithImpl<
          _$FinancialOverviewEntityImpl>(this, _$identity);
}

abstract class _FinancialOverviewEntity extends FinancialOverviewEntity {
  const factory _FinancialOverviewEntity(
      {required final List<FinancialTransactionEntity> items,
      required final int totalRevenue,
      required final int totalExpenses,
      required final double netIncome,
      required final int currentPage,
      required final int totalPages,
      required final int totalItems}) = _$FinancialOverviewEntityImpl;
  const _FinancialOverviewEntity._() : super._();

  @override
  List<FinancialTransactionEntity> get items;
  @override
  int get totalRevenue;
  @override
  int get totalExpenses;
  @override
  double get netIncome;
  @override
  int get currentPage;
  @override
  int get totalPages;
  @override
  int get totalItems;
  @override
  @JsonKey(ignore: true)
  _$$FinancialOverviewEntityImplCopyWith<_$FinancialOverviewEntityImpl>
      get copyWith => throw _privateConstructorUsedError;
}
