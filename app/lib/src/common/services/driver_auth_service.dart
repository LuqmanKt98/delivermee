import 'dart:async';

import 'package:get/get.dart';
import 'package:image_picker/image_picker.dart';
import '../../models/driver_model.dart';
import 'driver_api_service.dart';
import 'driver_document_service.dart';
import 'firebase_auth_service.dart';

class DriverAuthService extends GetxService {
  static DriverAuthService get to => Get.find<DriverAuthService>();

  final Rx<DriverModel?> currentDriver = Rx<DriverModel?>(null);
  final RxBool isLoggedIn = false.obs;
  final RxBool isLoading = false.obs;
  final RxBool isRegistering = false.obs;

  @override
  void onInit() {
    super.onInit();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    try {
      isLoading.value = true;
      if (!FirebaseAuthService.to.isSignedIn) return;
      final driver = await DriverApiService.getCurrentDriver();
      if (driver != null) {
        currentDriver.value = driver;
        isLoggedIn.value = true;
      }
    } catch (_) {
    } finally {
      isLoading.value = false;
    }
  }

  /// Firebase sign-up then backend profile creation.
  Future<DriverRegistrationResponse> register({
    required String email,
    required String password,
    required String phoneNumber,
    required String firstName,
    required String lastName,
    required String driverLicenseNumber,
    required String vehicleType,
    String? vehicleMake,
    String? vehicleModel,
    int? vehicleYear,
    String? vehiclePlateNumber,
    Map<String, XFile>? documents,
    bool isAvailable = true,
  }) async {
    try {
      isLoading.value = true;
      isRegistering.value = true;

      // 1. Create Firebase Auth account
      await FirebaseAuthService.to.signUpWithEmail(email, password);

      // 2. Create Firestore profile (email comes from Firebase token server-side)
      final response = await DriverApiService.register(
        phoneNumber: phoneNumber,
        firstName: firstName,
        lastName: lastName,
        driverLicenseNumber: driverLicenseNumber,
        vehicleType: vehicleType,
        vehicleMake: vehicleMake ?? 'Other',
        vehicleModel: vehicleModel ?? 'Unknown',
        vehicleYear: vehicleYear ?? DateTime.now().year,
        vehiclePlateNumber: vehiclePlateNumber ?? 'TBD',
        isAvailable: isAvailable,
      );

      // 3. Upload documents if provided
      if (documents != null &&
          documents.isNotEmpty &&
          response.driver.id != null) {
        try {
          final uploadResults =
              await DriverDocumentService.uploadDocumentsAfterRegistration(
            driverId: response.driver.id!,
            files: documents,
          );
          await DriverApiService.updateDocuments(
            drivingLicenseImage: uploadResults['driver_license'],
            idCardImage: uploadResults['id_card'],
          );
        } catch (_) {
          // Non-fatal — registration succeeded even if upload fails
        }
      }

      currentDriver.value = response.driver;
      return response;
    } catch (e) {
      rethrow;
    } finally {
      isLoading.value = false;
    }
  }

  /// Firebase sign-in then fetch profile from backend.
  Future<DriverModel> login(String email, String password) async {
    try {
      isLoading.value = true;

      await FirebaseAuthService.to.signInWithEmail(email, password);
      final driver = await DriverApiService.getProfile();

      currentDriver.value = driver;
      isLoggedIn.value = true;
      return driver;
    } catch (e) {
      rethrow;
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> logout() async {
    try {
      isLoading.value = true;
      await DriverApiService.logout(); // also calls FirebaseAuth.signOut()
      currentDriver.value = null;
      isLoggedIn.value = false;
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> refreshProfile() async {
    if (!isLoggedIn.value) return;
    try {
      isLoading.value = true;
      final driver = await DriverApiService.getProfile();
      currentDriver.value = driver;
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> checkLoginStatus() async {
    if (isRegistering.value) return false;
    final loggedIn = FirebaseAuthService.to.isSignedIn;
    isLoggedIn.value = loggedIn;
    if (loggedIn && currentDriver.value == null) await _restoreSession();
    return loggedIn;
  }

  Future<void> clearDriverData() async {
    await DriverApiService.logout();
    currentDriver.value = null;
    isLoggedIn.value = false;
  }

  Future<void> updateProfile(DriverModel driver) async {
    try {
      isLoading.value = true;
      await DriverApiService.updateProfile(
        firstName: driver.firstName,
        lastName: driver.lastName,
        phoneNumber: driver.phoneNumber,
      );
      currentDriver.value = driver;
    } finally {
      isLoading.value = false;
    }
  }

  DriverModel? get driver => currentDriver.value;
  int? get driverId => currentDriver.value?.id;
  bool get isDriverAvailable => currentDriver.value?.isAvailable ?? false;
  bool get hasPaymentMethod => currentDriver.value?.hasPaymentMethod ?? false;
  String get driverStatus => currentDriver.value?.status ?? 'offline';
  String get driverName {
    final d = currentDriver.value;
    if (d == null) return '';
    return '${d.firstName} ${d.lastName}';
  }

  String get driverEmail => currentDriver.value?.email ?? '';
  String get driverPhone => currentDriver.value?.phoneNumber ?? '';
  String get vehicleInfo {
    final d = currentDriver.value;
    if (d == null) return '';
    return '${d.vehicleYear} ${d.vehicleModel} ${d.vehicleColor}';
  }

  String get licenseNumber => currentDriver.value?.licenseNumber ?? '';
  double? get rating => currentDriver.value?.rating;
  int? get totalRides => currentDriver.value?.totalRides;
  bool get isActive => currentDriver.value?.isActive ?? false;
  bool get notificationEnabled =>
      currentDriver.value?.notificationEnabled ?? true;

  Map<String, double?> get currentLocation {
    final driver = currentDriver.value;
    return {
      'latitude': driver?.currentLatitude,
      'longitude': driver?.currentLongitude,
    };
  }
}
