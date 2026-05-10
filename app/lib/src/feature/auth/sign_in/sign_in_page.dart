import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/constant/validator.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/rich_text.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:deliver_mee/src/feature/auth/forgot_password/forgot_password_page.dart';
import 'package:deliver_mee/src/feature/auth/sign_up/sign_up_page.dart';
import 'package:deliver_mee/src/feature/driver/auth/pages/driver_unified_signup_screen.dart';
import 'package:deliver_mee/src/feature/driver/auth/controller/driver_auth_controller.dart';
import 'package:deliver_mee/src/feature/driver/driver_bottom_bar/pages/driver_bottom_bar_screen.dart';
import 'package:deliver_mee/src/feature/onboarding_screen/turn_on_location/turn_on_location.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

class SignInPage extends StatefulWidget {
  SignInPage({super.key});

  @override
  State<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends State<SignInPage> {
  final _formkey = GlobalKey<FormState>();
  final TextEditingController emailController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();

  // Driver controllers
  late TextEditingController _driverEmailController;
  late TextEditingController _driverPasswordController;

  @override
  void initState() {
    super.initState();
    _driverEmailController =
        TextEditingController(text: DriverAuthController.to.email.value);
    _driverPasswordController =
        TextEditingController(text: DriverAuthController.to.password.value);
  }

  @override
  void dispose() {
    _driverEmailController.dispose();
    _driverPasswordController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    if (_formkey.currentState!.validate()) {
      // Check if driver is selected
      if (AuthController.to.selectedIndex.value == 0) {
        // Driver login
        DriverAuthController.to.error.value = '';
        final success = await DriverAuthController.to.login();
        if (success) {
          Get.offAll(() => DriverBottomBarScreen());
        }
      } else {
        // Customer login
        AuthController.to.clearError();
        final success = await AuthController.to.login(
          emailController.text.trim(),
          passwordController.text.trim(),
        );
        if (success) {
          Get.offAll(TurnOnLocation(), transition: Transition.cupertino);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: AppColors.whiteColor,
      body: Padding(
        padding: EdgeInsets.all(15.h),
        child: Form(
          key: _formkey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  height: 30.h,
                ),
                Center(
                  child: Image.asset(
                    AppImages.logo,
                    height: 100.h,
                  ),
                ),
                SizedBox(
                  height: 50.h,
                ),
                TextWidget(
                  text: 'Sign In',
                  fontSize: 28.sp,
                  color: AppColors.naveBlue,
                ),
                SizedBox(
                  height: 30.h,
                ),
                TextWidget(
                  text: 'Email ',
                  fontSize: 14.sp,
                  color: AppColors.blackColor,
                  fontWeight: FontWeight.w600,
                ),
                SizedBox(
                  height: 10.h,
                ),
                Obx(() {
                  // Use driver controller fields when driver is selected
                  if (AuthController.to.selectedIndex.value == 0) {
                    return CustomTextFormField(
                      controller: _driverEmailController,
                      onChanged: (value) =>
                          DriverAuthController.to.updateField('email', value),
                      validator: (validator) => emailValidator(validator),
                      hint: 'Email',
                    );
                  } else {
                    return CustomTextFormField(
                      controller: emailController,
                      validator: (validator) => emailValidator(validator),
                      hint: 'Email',
                    );
                  }
                }),
                SizedBox(
                  height: 10.h,
                ),
                TextWidget(
                  text: 'Password',
                  fontSize: 14.sp,
                  color: AppColors.blackColor,
                  fontWeight: FontWeight.w600,
                ),
                SizedBox(
                  height: 10.h,
                ),
                Obx(() {
                  // Use driver controller fields when driver is selected
                  if (AuthController.to.selectedIndex.value == 0) {
                    return CustomTextFormField(
                      controller: _driverPasswordController,
                      onChanged: (value) => DriverAuthController.to
                          .updateField('password', value),
                      validator: (validator) => passwordValidator(validator),
                      hint: 'Your password',
                      obsecure: AuthController.to.isVisibility.value,
                      suffixIcon: GestureDetector(
                        onTap: () {
                          AuthController.to.setVisibility();
                        },
                        child: Icon(
                          AuthController.to.isVisibility.value
                              ? Icons.visibility_off
                              : Icons.visibility_outlined,
                          color: AppColors.greyTextColor.withOpacity(.7),
                        ),
                      ),
                    );
                  } else {
                    return CustomTextFormField(
                      controller: passwordController,
                      validator: (validator) => passwordValidator(validator),
                      hint: 'Your password',
                      obsecure: AuthController.to.isVisibility.value,
                      suffixIcon: GestureDetector(
                        onTap: () {
                          AuthController.to.setVisibility();
                        },
                        child: Icon(
                          AuthController.to.isVisibility.value
                              ? Icons.visibility_off
                              : Icons.visibility_outlined,
                          color: AppColors.greyTextColor.withOpacity(.7),
                        ),
                      ),
                    );
                  }
                }),
                SizedBox(
                  height: 15.h,
                ),
                Obx(() {
                  // Show driver error when driver is selected, customer error otherwise
                  String errorMessage = '';
                  if (AuthController.to.selectedIndex.value == 0) {
                    errorMessage = DriverAuthController.to.error.value;
                  } else {
                    errorMessage = AuthController.to.errorMessage.value;
                  }

                  if (errorMessage.isNotEmpty) {
                    return Container(
                      padding: EdgeInsets.all(12.h),
                      margin: EdgeInsets.only(bottom: 15.h),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8.r),
                        border: Border.all(color: Colors.red.withOpacity(0.3)),
                      ),
                      child: TextWidget(
                        text: errorMessage,
                        fontSize: 14.sp,
                        color: Colors.red,
                        textAlign: TextAlign.center,
                      ),
                    );
                  }
                  return SizedBox.shrink();
                }),
                InkWell(
                  onTap: () {
                    final userType =
                        AuthController.to.selectedIndex.value == 0
                            ? 'driver'
                            : 'customer';
                    Get.to(
                      ForgotPasswordPage(userType: userType),
                      transition: Transition.cupertino,
                    );
                  },
                  child: TextWidget(
                    text: 'Forgot Password?',
                    fontSize: 14.sp,
                    color: AppColors.primaryColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(
                  height: 25.h,
                ),
                Obx(() {
                  // Show appropriate loading state based on selected role
                  bool isLoading = false;
                  if (AuthController.to.selectedIndex.value == 0) {
                    isLoading = DriverAuthController.to.isLoading.value;
                  } else {
                    isLoading = AuthController.to.isLoading.value;
                  }

                  return Container(
                    width: double.infinity,
                    height: 90.h,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primaryColor,
                        padding: EdgeInsets.zero,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(100.r),
                        ),
                      ),
                      onPressed: isLoading ? null : _handleLogin,
                      child: TextWidget(
                        text: isLoading ? 'Logging in...' : 'Login',
                        color: AppColors.whiteColor,
                        fontSize: 18.sp,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }),
                SizedBox(
                  height: 30.h,
                ),
                Center(
                  child: GestureDetector(
                    onTap: () {
                      // Check if driver is selected, navigate to driver signup, otherwise customer signup
                      if (AuthController.to.selectedIndex.value == 0) {
                        // Driver selected
                        Get.to(() => const DriverUnifiedSignupScreen(),
                            transition: Transition.cupertino);
                      } else {
                        // Customer selected
                        Get.to(() => SignUpPage(),
                            transition: Transition.cupertino);
                      }
                    },
                    child: authRightText(
                        textOne: 'Don\'t have an account?', textTwo: 'Sign Up'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
