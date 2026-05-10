import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/constant/validator.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/common/services/driver_api_service.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DriverEditProfile extends StatefulWidget {
  const DriverEditProfile({super.key});

  @override
  State<DriverEditProfile> createState() => _DriverEditProfileState();
}

class _DriverEditProfileState extends State<DriverEditProfile> {
  TextEditingController fullname = TextEditingController();
  TextEditingController email = TextEditingController();
  TextEditingController phone = TextEditingController();
  TextEditingController password = TextEditingController();
  final _formkey = GlobalKey<FormState>();
  bool isLoading = false;
  bool isLoadingProfile = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final firstName = prefs.getString('first_name') ?? '';
      final lastName = prefs.getString('last_name') ?? '';
      final driverEmail = prefs.getString('email') ?? '';
      final phoneNumber = prefs.getString('phone_number') ?? '';

      setState(() {
        fullname.text = '$firstName $lastName'.trim();
        email.text = driverEmail;
        phone.text = phoneNumber;
        isLoadingProfile = false;
      });
    } catch (e) {
      print('Error loading profile: $e');
      setState(() {
        isLoadingProfile = false;
      });
    }
  }

  Future<void> _saveProfile() async {
    if (!_formkey.currentState!.validate()) {
      return;
    }

    setState(() {
      isLoading = true;
    });

    try {
      // Split full name into first and last name
      final nameParts = fullname.text.trim().split(' ');
      final firstName = nameParts.isNotEmpty ? nameParts[0] : '';
      final lastName =
          nameParts.length > 1 ? nameParts.sublist(1).join(' ') : '';

      final result = await DriverApiService.updateProfile(
        firstName: firstName,
        lastName: lastName,
        phoneNumber: phone.text.trim(),
        password: password.text.trim().isNotEmpty ? password.text.trim() : null,
      );

      setState(() {
        isLoading = false;
      });

      if (result['success'] == true) {
        Get.snackbar(
          'Success',
          result['message'] ?? 'Profile updated successfully',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green,
          colorText: Colors.white,
        );
        password.clear();
        Get.back();
      } else {
        Get.snackbar(
          'Error',
          result['error'] ?? 'Failed to update profile',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
      }
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      Get.snackbar(
        'Error',
        'An error occurred: ${e.toString()}',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoadingProfile) {
      return Scaffold(
        appBar: CustomAppBar(text: "Edit Profile", leading: true),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: CustomAppBar(text: "Edit Profile", leading: true),
      body: Padding(
        padding: EdgeInsets.all(16.w),
        child: Container(
          height: ScreenUtil().screenHeight,
          width: ScreenUtil().screenWidth,
          child: Form(
            key: _formkey,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  SizedBox(height: 10.h),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextWidget(
                      text: 'Edit Profile',
                      fontSize: 26.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.naveBlue,
                    ),
                  ),
                  SizedBox(height: 10.h),
                  SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextWidget(
                          text: 'Full Name',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 10.h),
                        CustomTextFormField(
                          controller: fullname,
                          prefixIcon: Padding(
                            padding: const EdgeInsets.all(12.0),
                            child: SvgPicture.asset(
                              AppIcons.profileIcon,
                              color: Colors.grey,
                            ),
                          ),
                          validator: (validator) => nameValidator(validator),
                          hint: 'Full Name',
                        ),
                        SizedBox(height: 20.h),
                        TextWidget(
                          text: 'Email',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 10.h),
                        CustomTextFormField(
                          controller: email,
                          validator: (value) => null,
                          enable: false,
                          prefixIcon: Padding(
                            padding: const EdgeInsets.all(12.0),
                            child: SvgPicture.asset(
                              AppIcons.mailprofileIcon,
                              color: Colors.grey,
                            ),
                          ),
                          hint: 'Email',
                        ),
                        SizedBox(height: 20.h),
                        TextWidget(
                          text: 'Phone',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 10.h),
                        CustomTextFormField(
                          controller: phone,
                          prefixIcon: Padding(
                            padding: const EdgeInsets.all(12.0),
                            child: SvgPicture.asset(
                              AppIcons.phoneprofileIcon,
                              color: Colors.grey,
                            ),
                          ),
                          validator: (validator) =>
                              validatePhoneNumber(validator),
                          hint: 'Phone',
                        ),
                        SizedBox(height: 20.h),
                        TextWidget(
                          text: 'Password (leave empty to keep current)',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 10.h),
                        Obx(
                          () => CustomTextFormField(
                            controller: password,
                            prefixIcon: Padding(
                              padding: const EdgeInsets.all(12.0),
                              child: SvgPicture.asset(
                                AppIcons.lockIcon,
                                color: Colors.grey,
                              ),
                            ),
                            obsecure: AuthController.to.isVisibility.value,
                            validator: (value) {
                              if (value != null &&
                                  value.isNotEmpty &&
                                  value.length < 6) {
                                return 'Password must be at least 6 characters';
                              }
                              return null;
                            },
                            hint: 'Password (optional)',
                            suffixIcon: GestureDetector(
                              onTap: () {
                                AuthController.to.setVisibility();
                              },
                              child: Icon(
                                AuthController.to.isVisibility.value
                                    ? Icons.visibility_off
                                    : Icons.visibility_outlined,
                                color: Colors.grey,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  SizedBox(height: 30.h),
                  isLoading
                      ? const CircularProgressIndicator()
                      : CustomButton(
                          text: 'Save Changes',
                          ontap: _saveProfile,
                        ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
