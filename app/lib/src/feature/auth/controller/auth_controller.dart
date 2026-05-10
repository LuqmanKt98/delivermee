import 'dart:async';
import 'dart:io';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:image_picker/image_picker.dart';
import '../../../common/services/api_service.dart';
import '../../../common/services/driver_api_service.dart';
import '../../../common/services/firebase_auth_service.dart';
import '../../../models/user_model.dart';

class AuthController extends GetxController {
  static AuthController get to => Get.find<AuthController>();

  // ── UI toggles ────────────────────────────────────────────────────────────
  var isSelected = true.obs;
  RxInt selectedIndex = 0.obs;
  void setSelectedIndex(int index) => selectedIndex.value = index;

  RxBool isVisibility = true.obs;
  void setVisibility() => isVisibility.value = !isVisibility.value;

  var password = ''.obs;
  bool get hasMinLength => password.value.length >= 8;
  bool get hasNumber => RegExp(r'[0-9]').hasMatch(password.value);
  bool get hasUppercase => RegExp(r'[A-Z]').hasMatch(password.value);

  RxBool passwordTwoVisibility = true.obs;
  void setPasswordtVisibility() =>
      passwordTwoVisibility.value = !passwordTwoVisibility.value;

  RxBool confirmpasswordTwoVisibility = true.obs;
  void setConfirmPasswordtVisibility() =>
      confirmpasswordTwoVisibility.value = !confirmpasswordTwoVisibility.value;

  RxInt otpMethod = 0.obs;
  void setOtpMethod(int index) => otpMethod.value = index;

  // ── Forgot-password UI state ──────────────────────────────────────────────
  RxInt selectedForgotIndex = 0.obs;
  void setSelectedForgotIndex(int index) => selectedForgotIndex.value = index;

  RxBool isForgotVisibility = false.obs;
  void setForgotVisibility() =>
      isForgotVisibility.value = !isForgotVisibility.value;

  RxBool newPassword = false.obs;
  void setNewPassword() => newPassword.value = !newPassword.value;

  RxBool newConfirmPassword = false.obs;
  void setNewConfirmPassword() =>
      newConfirmPassword.value = !newConfirmPassword.value;

  final RxBool isForgotLoading = false.obs;
  final RxString forgotError = ''.obs;

  // State carried across the forgot-password screens
  String forgotEmail = '';
  String forgotPhone = '';
  bool forgotIsPhone = false;
  String _phoneVerificationId = '';
  String forgotUserType = 'customer'; // 'customer' or 'driver'

  // ── Login / Register ──────────────────────────────────────────────────────
  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;

  Future<bool> login(String email, String password) async {
    try {
      isLoading.value = true;
      errorMessage.value = '';

      await FirebaseAuthService.to.signInWithEmail(email, password);
      await ApiService.fetchProfile();

      Get.snackbar(
        'Welcome Back!',
        'Login successful!',
        snackPosition: SnackPosition.TOP,
        backgroundColor: Colors.green,
        colorText: Colors.white,
        duration: const Duration(seconds: 3),
      );
      return true;
    } on FirebaseAuthException catch (e) {
      errorMessage.value = _firebaseMessage(e);
      _showError('Login Failed', errorMessage.value);
      return false;
    } on ApiError catch (e) {
      errorMessage.value = e.error;
      _showError('Login Failed', e.error);
      return false;
    } catch (e) {
      errorMessage.value = 'An unexpected error occurred';
      _showError('Error', errorMessage.value);
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> register({
    required String email,
    required String phoneNumber,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    try {
      isLoading.value = true;
      errorMessage.value = '';

      // 1. Create Firebase Auth account
      await FirebaseAuthService.to.signUpWithEmail(email, password);

      // 2. Send email verification (non-blocking)
      FirebaseAuthService.to.sendEmailVerification().catchError((_) {});

      // 3. Create Firestore profile via backend
      print('🔧 Creating Firestore profile with: $firstName $lastName $phoneNumber');
      try {
        await ApiService.createProfile(
          firstName: firstName,
          lastName: lastName,
          phoneNumber: phoneNumber,
        );
        print('✅ Firestore profile created successfully');
      } catch (e) {
        print('❌ Error creating Firestore profile: $e');
        rethrow;
      }

      Get.snackbar(
        'Success!',
        'Registration successful! Please verify your email.',
        snackPosition: SnackPosition.TOP,
        backgroundColor: Colors.green,
        colorText: Colors.white,
        duration: const Duration(seconds: 4),
      );
      return true;
    } on FirebaseAuthException catch (e) {
      errorMessage.value = _firebaseMessage(e);
      _showError('Registration Failed', errorMessage.value);
      return false;
    } on ApiError catch (e) {
      errorMessage.value = e.error;
      _showError('Registration Failed', e.error);
      return false;
    } catch (e) {
      errorMessage.value = 'An unexpected error occurred';
      _showError('Error', errorMessage.value);
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  // ── Forgot password — email flow (Firebase handles it) ────────────────────

  /// Send a Firebase password-reset email. [userType] is accepted but ignored
  /// (Firebase handles both customers and drivers the same way).
  Future<bool> sendForgotOtp(String email, String userType) async {
    try {
      isForgotLoading.value = true;
      forgotError.value = '';
      forgotEmail = email.trim();
      forgotIsPhone = false;
      forgotUserType = userType; // Store user type for later password reset

      await FirebaseAuthService.to.sendPasswordResetEmail(forgotEmail);
      return true;
    } on FirebaseAuthException catch (e) {
      forgotError.value = _firebaseMessage(e);
      return false;
    } catch (e) {
      forgotError.value = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      isForgotLoading.value = false;
    }
  }

  // ── Forgot password — phone OTP flow (Firebase SMS) ───────────────────────

  Future<bool> sendForgotOtpPhone(String phoneNumber, String userType) async {
    try {
      isForgotLoading.value = true;
      forgotError.value = '';
      forgotPhone = phoneNumber.trim();
      forgotIsPhone = true;
      forgotUserType = userType; // Store user type for later password reset

      final completer = Completer<bool>();

      await FirebaseAuthService.to.verifyPhoneNumber(
        phoneNumber: forgotPhone,
        verificationCompleted: (_) {
          if (!completer.isCompleted) completer.complete(true);
        },
        verificationFailed: (e) {
          if (!completer.isCompleted) {
            forgotError.value = _firebaseMessage(e);
            completer.complete(false);
          }
        },
        codeSent: (verificationId, _) {
          _phoneVerificationId = verificationId;
          if (!completer.isCompleted) completer.complete(true);
        },
        codeAutoRetrievalTimeout: (_) {},
      );

      return await completer.future;
    } catch (e) {
      forgotError.value = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      isForgotLoading.value = false;
    }
  }

  /// Verify the SMS OTP entered by the user.
  Future<bool> verifyForgotOtp(String otp) async {
    try {
      isForgotLoading.value = true;
      forgotError.value = '';

      if (!forgotIsPhone) {
        // Email flow: Firebase already sent a reset link — nothing to verify here.
        // The user clicks the link in their inbox; no code to confirm on this side.
        return true;
      }

      // Phone flow: confirm the SMS code (this verifies the OTP)
      await FirebaseAuthService.to.confirmPhoneCode(_phoneVerificationId, otp);
      return true;
    } on FirebaseAuthException catch (e) {
      forgotError.value = _firebaseMessage(e);
      return false;
    } catch (e) {
      forgotError.value = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      isForgotLoading.value = false;
    }
  }

  /// Set a new password after phone OTP verification.
  /// Uses backend API to securely update password via Firebase Admin SDK.
  Future<bool> resetForgotPassword(String newPwd) async {
    try {
      isForgotLoading.value = true;
      forgotError.value = '';

      print('🔧 Resetting password for $forgotUserType');

      // Call backend endpoint based on user type
      final Map<String, dynamic> response;
      if (forgotUserType == 'driver') {
        response = await DriverApiService.post('/reset-password', {
          'new_password': newPwd,
          'email': forgotEmail,
        });
      } else {
        response = await ApiService.post('/reset-password', {
          'new_password': newPwd,
          'email': forgotEmail,
        });
      }

      if (response['message'] != null) {
        // Sign out and navigate to login
        await FirebaseAuthService.to.signOut();
        forgotEmail = '';
        forgotPhone = '';
        forgotIsPhone = false;
        _phoneVerificationId = '';
        forgotUserType = 'customer'; // Reset to default
        print('✅ Password reset successfully');
        return true;
      } else {
        forgotError.value = response['error'] ?? 'Failed to reset password';
        print('❌ Password reset error: ${forgotError.value}');
        return false;
      }
    } on ApiError catch (e) {
      forgotError.value = e.error;
      print('❌ API Error: ${e.error}');
      return false;
    } catch (e) {
      // Handle both ApiError and DriverApiError generically
      if (e.toString().contains('error')) {
        forgotError.value = e.toString();
      } else {
        forgotError.value = e.toString().replaceFirst('Exception: ', '');
      }
      print('❌ Exception: ${forgotError.value}');
      return false;
    } finally {
      isForgotLoading.value = false;
    }
  }

  // ── Image picker ──────────────────────────────────────────────────────────

  File? image;
  final ImagePicker _picker = ImagePicker();

  Future<void> pickImage(ImageSource source) async {
    final XFile? pickedFile = await _picker.pickImage(source: source);
    if (pickedFile != null) {
      image = File(pickedFile.path);
      update(['imagepick']);
    }
  }

  File? imageTwo;
  final ImagePicker _pickerTwo = ImagePicker();

  Future<void> pickImageTwo(ImageSource source) async {
    final XFile? pickedFile = await _pickerTwo.pickImage(source: source);
    if (pickedFile != null) {
      imageTwo = File(pickedFile.path);
      update(['imagepicktwo']);
    }
  }

  // ── Car selection ─────────────────────────────────────────────────────────

  TextEditingController selectedCarCtrl = TextEditingController();
  RxString selectedCar = ''.obs;
  void saveTextOfCar(String text) {
    selectedCarCtrl.text = text;
    update(['getCarName']);
  }

  RxInt textIndex = 3.obs;
  void selectCar(String car, int index) {
    textIndex.value = index;
    selectedCar.value = car;
    update(['index']);
  }

  void clearError() => errorMessage.value = '';

  // ── Helpers ───────────────────────────────────────────────────────────────

  void _showError(String title, String message) {
    Get.snackbar(
      title,
      message,
      snackPosition: SnackPosition.TOP,
      backgroundColor: Colors.red,
      colorText: Colors.white,
      duration: const Duration(seconds: 4),
    );
  }

  String _firebaseMessage(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return 'No account found with this email.';
      case 'wrong-password':
        return 'Incorrect password.';
      case 'email-already-in-use':
        return 'This email is already registered.';
      case 'weak-password':
        return 'Password is too weak (minimum 6 characters).';
      case 'invalid-email':
        return 'Invalid email address.';
      case 'too-many-requests':
        return 'Too many attempts. Please try again later.';
      case 'invalid-verification-code':
        return 'Invalid OTP code.';
      default:
        return e.message ?? 'Authentication error.';
    }
  }
}
