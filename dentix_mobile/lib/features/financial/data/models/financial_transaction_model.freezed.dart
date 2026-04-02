// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'financial_transaction_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

FinancialTransactionModel _$FinancialTransactionModelFromJson(
    Map<String, dynamic> json) {
  return _FinancialTransactionModel.fromJson(json);
}

/// @nodoc
mixin _$FinancialTransactionModel {
  int get id => throw _privateConstructorUsedError;
  String get type => throw _privateConstructorUsedError;
  double get amount => throw _privateConstructorUsedError;
  String get date => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_id')
  int? get patientId => throw _privateConstructorUsedError;
  @JsonKey(name: 'patient_name')
  String? get patientName => throw _privateConstructorUsedError;
  @JsonKey(name: 'appointment_id')
  int? get appointmentId => throw _privateConstructorUsedError;
  @JsonKey(name: 'treatment_id')
  int? get treatmentId => throw _privateConstructorUsedError;
  String? get category => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FinancialTransactionModelCopyWith<FinancialTransactionModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FinancialTransactionModelCopyWith<$Res> {
  factory $FinancialTransactionModelCopyWith(FinancialTransactionModel value,
          $Res Function(FinancialTransactionModel) then) =
      _$FinancialTransactionModelCopyWithImpl<$Res, FinancialTransactionModel>;
  @useResult
  $Res call(
      {int id,
      String type,
      double amount,
      String date,
      String? description,
      @JsonKey(name: 'patient_id') int? patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'treatment_id') int? treatmentId,
      String? category,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$FinancialTransactionModelCopyWithImpl<$Res,
        $Val extends FinancialTransactionModel>
    implements $FinancialTransactionModelCopyWith<$Res> {
  _$FinancialTransactionModelCopyWithImpl(this._value, this._then);

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
              as String,
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
abstract class _$$FinancialTransactionModelImplCopyWith<$Res>
    implements $FinancialTransactionModelCopyWith<$Res> {
  factory _$$FinancialTransactionModelImplCopyWith(
          _$FinancialTransactionModelImpl value,
          $Res Function(_$FinancialTransactionModelImpl) then) =
      __$$FinancialTransactionModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String type,
      double amount,
      String date,
      String? description,
      @JsonKey(name: 'patient_id') int? patientId,
      @JsonKey(name: 'patient_name') String? patientName,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'treatment_id') int? treatmentId,
      String? category,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$FinancialTransactionModelImplCopyWithImpl<$Res>
    extends _$FinancialTransactionModelCopyWithImpl<$Res,
        _$FinancialTransactionModelImpl>
    implements _$$FinancialTransactionModelImplCopyWith<$Res> {
  __$$FinancialTransactionModelImplCopyWithImpl(
      _$FinancialTransactionModelImpl _value,
      $Res Function(_$FinancialTransactionModelImpl) _then)
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
    return _then(_$FinancialTransactionModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
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
@JsonSerializable()
class _$FinancialTransactionModelImpl extends _FinancialTransactionModel {
  const _$FinancialTransactionModelImpl(
      {required this.id,
      required this.type,
      required this.amount,
      required this.date,
      this.description,
      @JsonKey(name: 'patient_id') this.patientId,
      @JsonKey(name: 'patient_name') this.patientName,
      @JsonKey(name: 'appointment_id') this.appointmentId,
      @JsonKey(name: 'treatment_id') this.treatmentId,
      this.category,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt})
      : super._();

  factory _$FinancialTransactionModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$FinancialTransactionModelImplFromJson(json);

  @override
  final int id;
  @override
  final String type;
  @override
  final double amount;
  @override
  final String date;
  @override
  final String? description;
  @override
  @JsonKey(name: 'patient_id')
  final int? patientId;
  @override
  @JsonKey(name: 'patient_name')
  final String? patientName;
  @override
  @JsonKey(name: 'appointment_id')
  final int? appointmentId;
  @override
  @JsonKey(name: 'treatment_id')
  final int? treatmentId;
  @override
  final String? category;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'FinancialTransactionModel(id: $id, type: $type, amount: $amount, date: $date, description: $description, patientId: $patientId, patientName: $patientName, appointmentId: $appointmentId, treatmentId: $treatmentId, category: $category, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FinancialTransactionModelImpl &&
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

  @JsonKey(ignore: true)
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
  _$$FinancialTransactionModelImplCopyWith<_$FinancialTransactionModelImpl>
      get copyWith => __$$FinancialTransactionModelImplCopyWithImpl<
          _$FinancialTransactionModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FinancialTransactionModelImplToJson(
      this,
    );
  }
}

abstract class _FinancialTransactionModel extends FinancialTransactionModel {
  const factory _FinancialTransactionModel(
          {required final int id,
          required final String type,
          required final double amount,
          required final String date,
          final String? description,
          @JsonKey(name: 'patient_id') final int? patientId,
          @JsonKey(name: 'patient_name') final String? patientName,
          @JsonKey(name: 'appointment_id') final int? appointmentId,
          @JsonKey(name: 'treatment_id') final int? treatmentId,
          final String? category,
          @JsonKey(name: 'created_at') final String? createdAt,
          @JsonKey(name: 'updated_at') final String? updatedAt}) =
      _$FinancialTransactionModelImpl;
  const _FinancialTransactionModel._() : super._();

  factory _FinancialTransactionModel.fromJson(Map<String, dynamic> json) =
      _$FinancialTransactionModelImpl.fromJson;

  @override
  int get id;
  @override
  String get type;
  @override
  double get amount;
  @override
  String get date;
  @override
  String? get description;
  @override
  @JsonKey(name: 'patient_id')
  int? get patientId;
  @override
  @JsonKey(name: 'patient_name')
  String? get patientName;
  @override
  @JsonKey(name: 'appointment_id')
  int? get appointmentId;
  @override
  @JsonKey(name: 'treatment_id')
  int? get treatmentId;
  @override
  String? get category;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$FinancialTransactionModelImplCopyWith<_$FinancialTransactionModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

FinancialOverviewResponseModel _$FinancialOverviewResponseModelFromJson(
    Map<String, dynamic> json) {
  return _FinancialOverviewResponseModel.fromJson(json);
}

/// @nodoc
mixin _$FinancialOverviewResponseModel {
  List<FinancialTransactionModel> get items =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'total_revenue')
  int get totalRevenue => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_expenses')
  int get totalExpenses => throw _privateConstructorUsedError;
  @JsonKey(name: 'net_income')
  double get netIncome => throw _privateConstructorUsedError;
  @JsonKey(name: 'current_page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_pages')
  int get totalPages => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_items')
  int get totalItems => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FinancialOverviewResponseModelCopyWith<FinancialOverviewResponseModel>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FinancialOverviewResponseModelCopyWith<$Res> {
  factory $FinancialOverviewResponseModelCopyWith(
          FinancialOverviewResponseModel value,
          $Res Function(FinancialOverviewResponseModel) then) =
      _$FinancialOverviewResponseModelCopyWithImpl<$Res,
          FinancialOverviewResponseModel>;
  @useResult
  $Res call(
      {List<FinancialTransactionModel> items,
      @JsonKey(name: 'total_revenue') int totalRevenue,
      @JsonKey(name: 'total_expenses') int totalExpenses,
      @JsonKey(name: 'net_income') double netIncome,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class _$FinancialOverviewResponseModelCopyWithImpl<$Res,
        $Val extends FinancialOverviewResponseModel>
    implements $FinancialOverviewResponseModelCopyWith<$Res> {
  _$FinancialOverviewResponseModelCopyWithImpl(this._value, this._then);

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
              as List<FinancialTransactionModel>,
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
abstract class _$$FinancialOverviewResponseModelImplCopyWith<$Res>
    implements $FinancialOverviewResponseModelCopyWith<$Res> {
  factory _$$FinancialOverviewResponseModelImplCopyWith(
          _$FinancialOverviewResponseModelImpl value,
          $Res Function(_$FinancialOverviewResponseModelImpl) then) =
      __$$FinancialOverviewResponseModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<FinancialTransactionModel> items,
      @JsonKey(name: 'total_revenue') int totalRevenue,
      @JsonKey(name: 'total_expenses') int totalExpenses,
      @JsonKey(name: 'net_income') double netIncome,
      @JsonKey(name: 'current_page') int currentPage,
      @JsonKey(name: 'total_pages') int totalPages,
      @JsonKey(name: 'total_items') int totalItems});
}

/// @nodoc
class __$$FinancialOverviewResponseModelImplCopyWithImpl<$Res>
    extends _$FinancialOverviewResponseModelCopyWithImpl<$Res,
        _$FinancialOverviewResponseModelImpl>
    implements _$$FinancialOverviewResponseModelImplCopyWith<$Res> {
  __$$FinancialOverviewResponseModelImplCopyWithImpl(
      _$FinancialOverviewResponseModelImpl _value,
      $Res Function(_$FinancialOverviewResponseModelImpl) _then)
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
    return _then(_$FinancialOverviewResponseModelImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<FinancialTransactionModel>,
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
@JsonSerializable()
class _$FinancialOverviewResponseModelImpl
    extends _FinancialOverviewResponseModel {
  const _$FinancialOverviewResponseModelImpl(
      {required final List<FinancialTransactionModel> items,
      @JsonKey(name: 'total_revenue') required this.totalRevenue,
      @JsonKey(name: 'total_expenses') required this.totalExpenses,
      @JsonKey(name: 'net_income') required this.netIncome,
      @JsonKey(name: 'current_page') required this.currentPage,
      @JsonKey(name: 'total_pages') required this.totalPages,
      @JsonKey(name: 'total_items') required this.totalItems})
      : _items = items,
        super._();

  factory _$FinancialOverviewResponseModelImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$FinancialOverviewResponseModelImplFromJson(json);

  final List<FinancialTransactionModel> _items;
  @override
  List<FinancialTransactionModel> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  @JsonKey(name: 'total_revenue')
  final int totalRevenue;
  @override
  @JsonKey(name: 'total_expenses')
  final int totalExpenses;
  @override
  @JsonKey(name: 'net_income')
  final double netIncome;
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
    return 'FinancialOverviewResponseModel(items: $items, totalRevenue: $totalRevenue, totalExpenses: $totalExpenses, netIncome: $netIncome, currentPage: $currentPage, totalPages: $totalPages, totalItems: $totalItems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FinancialOverviewResponseModelImpl &&
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

  @JsonKey(ignore: true)
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
  _$$FinancialOverviewResponseModelImplCopyWith<
          _$FinancialOverviewResponseModelImpl>
      get copyWith => __$$FinancialOverviewResponseModelImplCopyWithImpl<
          _$FinancialOverviewResponseModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FinancialOverviewResponseModelImplToJson(
      this,
    );
  }
}

abstract class _FinancialOverviewResponseModel
    extends FinancialOverviewResponseModel {
  const factory _FinancialOverviewResponseModel(
          {required final List<FinancialTransactionModel> items,
          @JsonKey(name: 'total_revenue') required final int totalRevenue,
          @JsonKey(name: 'total_expenses') required final int totalExpenses,
          @JsonKey(name: 'net_income') required final double netIncome,
          @JsonKey(name: 'current_page') required final int currentPage,
          @JsonKey(name: 'total_pages') required final int totalPages,
          @JsonKey(name: 'total_items') required final int totalItems}) =
      _$FinancialOverviewResponseModelImpl;
  const _FinancialOverviewResponseModel._() : super._();

  factory _FinancialOverviewResponseModel.fromJson(Map<String, dynamic> json) =
      _$FinancialOverviewResponseModelImpl.fromJson;

  @override
  List<FinancialTransactionModel> get items;
  @override
  @JsonKey(name: 'total_revenue')
  int get totalRevenue;
  @override
  @JsonKey(name: 'total_expenses')
  int get totalExpenses;
  @override
  @JsonKey(name: 'net_income')
  double get netIncome;
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
  _$$FinancialOverviewResponseModelImplCopyWith<
          _$FinancialOverviewResponseModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

RecordPaymentRequestModel _$RecordPaymentRequestModelFromJson(
    Map<String, dynamic> json) {
  return _RecordPaymentRequestModel.fromJson(json);
}

/// @nodoc
mixin _$RecordPaymentRequestModel {
  @JsonKey(name: 'patient_id')
  int get patientId => throw _privateConstructorUsedError;
  double get amount => throw _privateConstructorUsedError;
  String get date => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'appointment_id')
  int? get appointmentId => throw _privateConstructorUsedError;
  @JsonKey(name: 'treatment_id')
  int? get treatmentId => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $RecordPaymentRequestModelCopyWith<RecordPaymentRequestModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RecordPaymentRequestModelCopyWith<$Res> {
  factory $RecordPaymentRequestModelCopyWith(RecordPaymentRequestModel value,
          $Res Function(RecordPaymentRequestModel) then) =
      _$RecordPaymentRequestModelCopyWithImpl<$Res, RecordPaymentRequestModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      double amount,
      String date,
      String? description,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'treatment_id') int? treatmentId});
}

/// @nodoc
class _$RecordPaymentRequestModelCopyWithImpl<$Res,
        $Val extends RecordPaymentRequestModel>
    implements $RecordPaymentRequestModelCopyWith<$Res> {
  _$RecordPaymentRequestModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? amount = null,
    Object? date = null,
    Object? description = freezed,
    Object? appointmentId = freezed,
    Object? treatmentId = freezed,
  }) {
    return _then(_value.copyWith(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
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
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      treatmentId: freezed == treatmentId
          ? _value.treatmentId
          : treatmentId // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$RecordPaymentRequestModelImplCopyWith<$Res>
    implements $RecordPaymentRequestModelCopyWith<$Res> {
  factory _$$RecordPaymentRequestModelImplCopyWith(
          _$RecordPaymentRequestModelImpl value,
          $Res Function(_$RecordPaymentRequestModelImpl) then) =
      __$$RecordPaymentRequestModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'patient_id') int patientId,
      double amount,
      String date,
      String? description,
      @JsonKey(name: 'appointment_id') int? appointmentId,
      @JsonKey(name: 'treatment_id') int? treatmentId});
}

/// @nodoc
class __$$RecordPaymentRequestModelImplCopyWithImpl<$Res>
    extends _$RecordPaymentRequestModelCopyWithImpl<$Res,
        _$RecordPaymentRequestModelImpl>
    implements _$$RecordPaymentRequestModelImplCopyWith<$Res> {
  __$$RecordPaymentRequestModelImplCopyWithImpl(
      _$RecordPaymentRequestModelImpl _value,
      $Res Function(_$RecordPaymentRequestModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? patientId = null,
    Object? amount = null,
    Object? date = null,
    Object? description = freezed,
    Object? appointmentId = freezed,
    Object? treatmentId = freezed,
  }) {
    return _then(_$RecordPaymentRequestModelImpl(
      patientId: null == patientId
          ? _value.patientId
          : patientId // ignore: cast_nullable_to_non_nullable
              as int,
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
      appointmentId: freezed == appointmentId
          ? _value.appointmentId
          : appointmentId // ignore: cast_nullable_to_non_nullable
              as int?,
      treatmentId: freezed == treatmentId
          ? _value.treatmentId
          : treatmentId // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$RecordPaymentRequestModelImpl extends _RecordPaymentRequestModel {
  const _$RecordPaymentRequestModelImpl(
      {@JsonKey(name: 'patient_id') required this.patientId,
      required this.amount,
      required this.date,
      this.description,
      @JsonKey(name: 'appointment_id') this.appointmentId,
      @JsonKey(name: 'treatment_id') this.treatmentId})
      : super._();

  factory _$RecordPaymentRequestModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$RecordPaymentRequestModelImplFromJson(json);

  @override
  @JsonKey(name: 'patient_id')
  final int patientId;
  @override
  final double amount;
  @override
  final String date;
  @override
  final String? description;
  @override
  @JsonKey(name: 'appointment_id')
  final int? appointmentId;
  @override
  @JsonKey(name: 'treatment_id')
  final int? treatmentId;

  @override
  String toString() {
    return 'RecordPaymentRequestModel(patientId: $patientId, amount: $amount, date: $date, description: $description, appointmentId: $appointmentId, treatmentId: $treatmentId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RecordPaymentRequestModelImpl &&
            (identical(other.patientId, patientId) ||
                other.patientId == patientId) &&
            (identical(other.amount, amount) || other.amount == amount) &&
            (identical(other.date, date) || other.date == date) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.appointmentId, appointmentId) ||
                other.appointmentId == appointmentId) &&
            (identical(other.treatmentId, treatmentId) ||
                other.treatmentId == treatmentId));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, patientId, amount, date,
      description, appointmentId, treatmentId);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$RecordPaymentRequestModelImplCopyWith<_$RecordPaymentRequestModelImpl>
      get copyWith => __$$RecordPaymentRequestModelImplCopyWithImpl<
          _$RecordPaymentRequestModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RecordPaymentRequestModelImplToJson(
      this,
    );
  }
}

abstract class _RecordPaymentRequestModel extends RecordPaymentRequestModel {
  const factory _RecordPaymentRequestModel(
          {@JsonKey(name: 'patient_id') required final int patientId,
          required final double amount,
          required final String date,
          final String? description,
          @JsonKey(name: 'appointment_id') final int? appointmentId,
          @JsonKey(name: 'treatment_id') final int? treatmentId}) =
      _$RecordPaymentRequestModelImpl;
  const _RecordPaymentRequestModel._() : super._();

  factory _RecordPaymentRequestModel.fromJson(Map<String, dynamic> json) =
      _$RecordPaymentRequestModelImpl.fromJson;

  @override
  @JsonKey(name: 'patient_id')
  int get patientId;
  @override
  double get amount;
  @override
  String get date;
  @override
  String? get description;
  @override
  @JsonKey(name: 'appointment_id')
  int? get appointmentId;
  @override
  @JsonKey(name: 'treatment_id')
  int? get treatmentId;
  @override
  @JsonKey(ignore: true)
  _$$RecordPaymentRequestModelImplCopyWith<_$RecordPaymentRequestModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
