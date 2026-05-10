import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/constant/validator.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/common/utils/show_snack_bar.dart';
import 'package:deliver_mee/src/common/services/customer_service.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _UserProfileScreenState();
}

class _UserProfileScreenState extends State<EditProfileScreen> {
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
    setState(() {
      isLoadingProfile = true;
    });

    try {
      // Fetch fresh profile data from API
      final customerService = Get.find<CustomerService>();
      final result = await customerService.getProfile();

      if (result['success']) {
        final customer = result['data'];
        
        setState(() {
          fullname.text = '${customer['first_name'] ?? ''} ${customer['last_name'] ?? ''}'.trim();
          email.text = customer['email'] ?? '';
          phone.text = customer['phone_number'] ?? '';
          isLoadingProfile = false;
        });
        
        print('✅ Profile loaded successfully');
      } else {
        // Fallback to SharedPreferences if API fails
        print('⚠️ API failed, loading from SharedPreferences');
        final prefs = await SharedPreferences.getInstance();
        final firstName = prefs.getString('first_name') ?? '';
        final lastName = prefs.getString('last_name') ?? '';
        final userEmail = prefs.getString('email') ?? '';
        final phoneNumber = prefs.getString('phone_number') ?? '';

        setState(() {
          fullname.text = '$firstName $lastName'.trim();
          email.text = userEmail;
          phone.text = phoneNumber;
          isLoadingProfile = false;
        });
      }
    } catch (e) {
      print('❌ Error loading profile: $e');
      
      // Fallback to SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      final firstName = prefs.getString('first_name') ?? '';
      final lastName = prefs.getString('last_name') ?? '';
      final userEmail = prefs.getString('email') ?? '';
      final phoneNumber = prefs.getString('phone_number') ?? '';

      setState(() {
        fullname.text = '$firstName $lastName'.trim();
        email.text = userEmail;
        phone.text = phoneNumber;
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
      final lastName = nameParts.length > 1 ? nameParts.sublist(1).join(' ') : '';

      print('📝 Updating profile: $firstName $lastName, ${phone.text}');

      final customerService = Get.find<CustomerService>();
      final result = await customerService.updateProfile(
        firstName: firstName,
        lastName: lastName,
        phoneNumber: phone.text.trim(),
        password: password.text.isNotEmpty ? password.text : null,
      );

      setState(() {
        isLoading = false;
      });

      if (result['success']) {
        password.clear();
        // Reload profile to get fresh data
        await _loadProfile();

        Get.snackbar(
          'Success',
          result['message'] ?? 'Profile updated successfully',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.green,
          colorText: Colors.white,
          duration: Duration(seconds: 2),
        );

        // Wait a bit for user to see the success message
        await Future.delayed(Duration(milliseconds: 500));
        Get.back();
      } else {
        Get.snackbar(
          'Error',
          result['error'] ?? 'Failed to update profile',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.red,
          colorText: Colors.white,
          duration: Duration(seconds: 3),
        );
      }
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      print('❌ Save profile error: $e');
      Get.snackbar(
        'Error',
        'An error occurred: ${e.toString()}',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
        duration: Duration(seconds: 3),
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
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextWidget(
                      text: 'Edit Profile',
                      fontSize: 26.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.naveBlue,
                    ),
                  ),
                  SizedBox(
                    height: 10.h,
                  ),
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
                        SizedBox(
                          height: 10.h,
                        ),
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
                        SizedBox(
                          height: 20.h,
                        ),
                        TextWidget(
                          text: 'Email',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(
                          height: 10.h,
                        ),
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
                        SizedBox(
                          height: 20.h,
                        ),
                        TextWidget(
                          text: 'Phone',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(
                          height: 10.h,
                        ),
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
                        SizedBox(
                          height: 20.h,
                        ),
                        TextWidget(
                          text: 'Password (leave empty to keep current)',
                          fontSize: 14.sp,
                          color: AppColors.blackColor,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(
                          height: 10.h,
                        ),
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
                              if (value != null && value.isNotEmpty && value.length < 6) {
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
                  SizedBox(
                    height: 30.h,
                  ),
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
