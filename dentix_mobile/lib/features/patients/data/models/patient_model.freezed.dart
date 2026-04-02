// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'patient_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

PatientModel _$PatientModelFromJson(Map<String, dynamic> json) {
  return _PatientModel.fromJson(json);
}

/// @nodoc
mixin _$PatientModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'full_name')
  String get fullName => throw _privateConstructorUsedError;
  @JsonKey(name: 'phone')
  String? get phone => throw _privateConstructorUsedError;
  @JsonKey(name: 'email')
  String? get email => throw _privateConstructorUsedError;
  @JsonKey(name: 'date_of_birth')
  String? get dateOfBirth => throw _privateConstructorUsedError;
  @JsonKey(name: 'gender')
  String? get gender => throw _privateConstructorUsedError;
  @JsonKey(name: 'address')
  String? get address => throw _privateConstructorUsedError;
  @JsonKey(name: 'medical_history')
  String? get medicalHistory => throw _privateConstructorUsedError;
  @JsonKey(name: 'allergies')
  String? get allergies => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String? get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $PatientModelCopyWith<PatientModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PatientModelCopyWith<$Res> {
  factory $PatientModelCopyWith(
          PatientModel value, $Res Function(PatientModel) then) =
      _$PatientModelCopyWithImpl<$Res, PatientModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'full_name') String fullName,
      @JsonKey(name: 'phone') String? phone,
      @JsonKey(name: 'email') String? email,
      @JsonKey(name: 'date_of_birth') String? dateOfBirth,
      @JsonKey(name: 'gender') String? gender,
      @JsonKey(name: 'address') String? address,
      @JsonKey(name: 'medical_history') String? medicalHistory,
      @JsonKey(name: 'allergies') String? allergies,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class _$PatientModelCopyWithImpl<$Res, $Val extends PatientModel>
    implements $PatientModelCopyWith<$Res> {
  _$PatientModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? fullName = null,
    Object? phone = freezed,
    Object? email = freezed,
    Object? dateOfBirth = freezed,
    Object? gender = freezed,
    Object? address = freezed,
    Object? medicalHistory = freezed,
    Object? allergies = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      fullName: null == fullName
          ? _value.fullName
          : fullName // ignore: cast_nullable_to_non_nullable
              as String,
      phone: freezed == phone
          ? _value.phone
          : phone // ignore: cast_nullable_to_non_nullable
              as String?,
      email: freezed == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String?,
      dateOfBirth: freezed == dateOfBirth
          ? _value.dateOfBirth
          : dateOfBirth // ignore: cast_nullable_to_non_nullable
              as String?,
      gender: freezed == gender
          ? _value.gender
          : gender // ignore: cast_nullable_to_non_nullable
              as String?,
      address: freezed == address
          ? _value.address
          : address // ignore: cast_nullable_to_non_nullable
              as String?,
      medicalHistory: freezed == medicalHistory
          ? _value.medicalHistory
          : medicalHistory // ignore: cast_nullable_to_non_nullable
              as String?,
      allergies: freezed == allergies
          ? _value.allergies
          : allergies // ignore: cast_nullable_to_non_nullable
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
abstract class _$$PatientModelImplCopyWith<$Res>
    implements $PatientModelCopyWith<$Res> {
  factory _$$PatientModelImplCopyWith(
          _$PatientModelImpl value, $Res Function(_$PatientModelImpl) then) =
      __$$PatientModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'full_name') String fullName,
      @JsonKey(name: 'phone') String? phone,
      @JsonKey(name: 'email') String? email,
      @JsonKey(name: 'date_of_birth') String? dateOfBirth,
      @JsonKey(name: 'gender') String? gender,
      @JsonKey(name: 'address') String? address,
      @JsonKey(name: 'medical_history') String? medicalHistory,
      @JsonKey(name: 'allergies') String? allergies,
      @JsonKey(name: 'created_at') String? createdAt,
      @JsonKey(name: 'updated_at') String? updatedAt});
}

/// @nodoc
class __$$PatientModelImplCopyWithImpl<$Res>
    extends _$PatientModelCopyWithImpl<$Res, _$PatientModelImpl>
    implements _$$PatientModelImplCopyWith<$Res> {
  __$$PatientModelImplCopyWithImpl(
      _$PatientModelImpl _value, $Res Function(_$PatientModelImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? fullName = null,
    Object? phone = freezed,
    Object? email = freezed,
    Object? dateOfBirth = freezed,
    Object? gender = freezed,
    Object? address = freezed,
    Object? medicalHistory = freezed,
    Object? allergies = freezed,
    Object? createdAt = freezed,
    Object? updatedAt = freezed,
  }) {
    return _then(_$PatientModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      fullName: null == fullName
          ? _value.fullName
          : fullName // ignore: cast_nullable_to_non_nullable
              as String,
      phone: freezed == phone
          ? _value.phone
          : phone // ignore: cast_nullable_to_non_nullable
              as String?,
      email: freezed == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String?,
      dateOfBirth: freezed == dateOfBirth
          ? _value.dateOfBirth
          : dateOfBirth // ignore: cast_nullable_to_non_nullable
              as String?,
      gender: freezed == gender
          ? _value.gender
          : gender // ignore: cast_nullable_to_non_nullable
              as String?,
      address: freezed == address
          ? _value.address
          : address // ignore: cast_nullable_to_non_nullable
              as String?,
      medicalHistory: freezed == medicalHistory
          ? _value.medicalHistory
          : medicalHistory // ignore: cast_nullable_to_non_nullable
              as String?,
      allergies: freezed == allergies
          ? _value.allergies
          : allergies // ignore: cast_nullable_to_non_nullable
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
class _$PatientModelImpl implements _PatientModel {
  const _$PatientModelImpl(
      {required this.id,
      @JsonKey(name: 'full_name') required this.fullName,
      @JsonKey(name: 'phone') this.phone,
      @JsonKey(name: 'email') this.email,
      @JsonKey(name: 'date_of_birth') this.dateOfBirth,
      @JsonKey(name: 'gender') this.gender,
      @JsonKey(name: 'address') this.address,
      @JsonKey(name: 'medical_history') this.medicalHistory,
      @JsonKey(name: 'allergies') this.allergies,
      @JsonKey(name: 'created_at') this.createdAt,
      @JsonKey(name: 'updated_at') this.updatedAt});

  factory _$PatientModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$PatientModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'full_name')
  final String fullName;
  @override
  @JsonKey(name: 'phone')
  final String? phone;
  @override
  @JsonKey(name: 'email')
  final String? email;
  @override
  @JsonKey(name: 'date_of_birth')
  final String? dateOfBirth;
  @override
  @JsonKey(name: 'gender')
  final String? gender;
  @override
  @JsonKey(name: 'address')
  final String? address;
  @override
  @JsonKey(name: 'medical_history')
  final String? medicalHistory;
  @override
  @JsonKey(name: 'allergies')
  final String? allergies;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String? updatedAt;

  @override
  String toString() {
    return 'PatientModel(id: $id, fullName: $fullName, phone: $phone, email: $email, dateOfBirth: $dateOfBirth, gender: $gender, address: $address, medicalHistory: $medicalHistory, allergies: $allergies, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PatientModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.fullName, fullName) ||
                other.fullName == fullName) &&
            (identical(other.phone, phone) || other.phone == phone) &&
            (identical(other.email, email) || other.email == email) &&
            (identical(other.dateOfBirth, dateOfBirth) ||
                other.dateOfBirth == dateOfBirth) &&
            (identical(other.gender, gender) || other.gender == gender) &&
            (identical(other.address, address) || other.address == address) &&
            (identical(other.medicalHistory, medicalHistory) ||
                other.medicalHistory == medicalHistory) &&
            (identical(other.allergies, allergies) ||
                other.allergies == allergies) &&
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
      fullName,
      phone,
      email,
      dateOfBirth,
      gender,
      address,
      medicalHistory,
      allergies,
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PatientModelImplCopyWith<_$PatientModelImpl> get copyWith =>
      __$$PatientModelImplCopyWithImpl<_$PatientModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PatientModelImplToJson(
      this,
    );
  }
}

abstract class _PatientModel implements PatientModel {
  const factory _PatientModel(
          {required final int id,
          @JsonKey(name: 'full_name') required final String fullName,
          @JsonKey(name: 'phone') final String? phone,
          @JsonKey(name: 'email') final String? email,
          @JsonKey(name: 'date_of_birth') final String? dateOfBirth,
          @JsonKey(name: 'gender') final String? gender,
          @JsonKey(name: 'address') final String? address,
          @JsonKey(name: 'medical_history') final String? medicalHistory,
          @JsonKey(name: 'allergies') final String? allergies,
          @JsonKey(name: 'created_at') final String? createdAt,
          @JsonKey(name: 'updated_at') final String? updatedAt}) =
      _$PatientModelImpl;

  factory _PatientModel.fromJson(Map<String, dynamic> json) =
      _$PatientModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'full_name')
  String get fullName;
  @override
  @JsonKey(name: 'phone')
  String? get phone;
  @override
  @JsonKey(name: 'email')
  String? get email;
  @override
  @JsonKey(name: 'date_of_birth')
  String? get dateOfBirth;
  @override
  @JsonKey(name: 'gender')
  String? get gender;
  @override
  @JsonKey(name: 'address')
  String? get address;
  @override
  @JsonKey(name: 'medical_history')
  String? get medicalHistory;
  @override
  @JsonKey(name: 'allergies')
  String? get allergies;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String? get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$PatientModelImplCopyWith<_$PatientModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PatientListResponse _$PatientListResponseFromJson(Map<String, dynamic> json) {
  return _PatientListResponse.fromJson(json);
}

/// @nodoc
mixin _$PatientListResponse {
  List<PatientModel> get items => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;
  @JsonKey(name: 'page')
  int get currentPage => throw _privateConstructorUsedError;
  @JsonKey(name: 'pages')
  int get totalPages => throw _privateConstructorUsedError;
  @JsonKey(name: 'size')
  int get pageSize => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $PatientListResponseCopyWith<PatientListResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PatientListResponseCopyWith<$Res> {
  factory $PatientListResponseCopyWith(
          PatientListResponse value, $Res Function(PatientListResponse) then) =
      _$PatientListResponseCopyWithImpl<$Res, PatientListResponse>;
  @useResult
  $Res call(
      {List<PatientModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages,
      @JsonKey(name: 'size') int pageSize});
}

/// @nodoc
class _$PatientListResponseCopyWithImpl<$Res, $Val extends PatientListResponse>
    implements $PatientListResponseCopyWith<$Res> {
  _$PatientListResponseCopyWithImpl(this._value, this._then);

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
    Object? pageSize = null,
  }) {
    return _then(_value.copyWith(
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<PatientModel>,
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
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$PatientListResponseImplCopyWith<$Res>
    implements $PatientListResponseCopyWith<$Res> {
  factory _$$PatientListResponseImplCopyWith(_$PatientListResponseImpl value,
          $Res Function(_$PatientListResponseImpl) then) =
      __$$PatientListResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<PatientModel> items,
      int total,
      @JsonKey(name: 'page') int currentPage,
      @JsonKey(name: 'pages') int totalPages,
      @JsonKey(name: 'size') int pageSize});
}

/// @nodoc
class __$$PatientListResponseImplCopyWithImpl<$Res>
    extends _$PatientListResponseCopyWithImpl<$Res, _$PatientListResponseImpl>
    implements _$$PatientListResponseImplCopyWith<$Res> {
  __$$PatientListResponseImplCopyWithImpl(_$PatientListResponseImpl _value,
      $Res Function(_$PatientListResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? currentPage = null,
    Object? totalPages = null,
    Object? pageSize = null,
  }) {
    return _then(_$PatientListResponseImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<PatientModel>,
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
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$PatientListResponseImpl implements _PatientListResponse {
  const _$PatientListResponseImpl(
      {required final List<PatientModel> items,
      required this.total,
      @JsonKey(name: 'page') required this.currentPage,
      @JsonKey(name: 'pages') required this.totalPages,
      @JsonKey(name: 'size') required this.pageSize})
      : _items = items;

  factory _$PatientListResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$PatientListResponseImplFromJson(json);

  final List<PatientModel> _items;
  @override
  List<PatientModel> get items {
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
  @JsonKey(name: 'size')
  final int pageSize;

  @override
  String toString() {
    return 'PatientListResponse(items: $items, total: $total, currentPage: $currentPage, totalPages: $totalPages, pageSize: $pageSize)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PatientListResponseImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.total, total) || other.total == total) &&
            (identical(other.currentPage, currentPage) ||
                other.currentPage == currentPage) &&
            (identical(other.totalPages, totalPages) ||
                other.totalPages == totalPages) &&
            (identical(other.pageSize, pageSize) ||
                other.pageSize == pageSize));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_items),
      total,
      currentPage,
      totalPages,
      pageSize);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$PatientListResponseImplCopyWith<_$PatientListResponseImpl> get copyWith =>
      __$$PatientListResponseImplCopyWithImpl<_$PatientListResponseImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PatientListResponseImplToJson(
      this,
    );
  }
}

abstract class _PatientListResponse implements PatientListResponse {
  const factory _PatientListResponse(
          {required final List<PatientModel> items,
          required final int total,
          @JsonKey(name: 'page') required final int currentPage,
          @JsonKey(name: 'pages') required final int totalPages,
          @JsonKey(name: 'size') required final int pageSize}) =
      _$PatientListResponseImpl;

  factory _PatientListResponse.fromJson(Map<String, dynamic> json) =
      _$PatientListResponseImpl.fromJson;

  @override
  List<PatientModel> get items;
  @override
  int get total;
  @override
  @JsonKey(name: 'page')
  int get currentPage;
  @override
  @JsonKey(name: 'pages')
  int get totalPages;
  @override
  @JsonKey(name: 'size')
  int get pageSize;
  @override
  @JsonKey(ignore: true)
  _$$PatientListResponseImplCopyWith<_$PatientListResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
