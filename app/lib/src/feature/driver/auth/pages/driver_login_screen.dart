import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import '../../../../common/constant/app_colors.dart';
import '../../../../common/constant/app_images.dart';
import '../../../../common/utils/custom_button.dart';
import '../../../auth/forgot_password/forgot_password_page.dart';
import '../controller/driver_auth_controller.dart';
import 'driver_unified_signup_screen.dart';

class DriverLoginScreen extends StatefulWidget {
  const DriverLoginScreen({super.key});

  @override
  State<DriverLoginScreen> createState() => _DriverLoginScreenState();
}

class _DriverLoginScreenState extends State<DriverLoginScreen> {
  late TextEditingController _emailController;
  late TextEditingController _passwordController;
  late DriverAuthController _controller;
  bool _isPasswordVisible = false;

  @override
  void initState() {
    super.initState();
    _controller = DriverAuthController.to;
    _emailController = TextEditingController(text: _controller.email.value);
    _passwordController =
        TextEditingController(text: _controller.password.value);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(20.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: 40.h),

              // Logo and title
              Center(
                child: Column(
                  children: [
                    Image.asset(
                      AppImages.logo,
                      width: 80.w,
                      height: 80.h,
                    ),
                    SizedBox(height: 20.h),
                    Text(
                      'Driver Login',
                      style: TextStyle(
                        fontSize: 28.sp,
                        fontWeight: FontWeight.bold,
                        color: AppColors.primaryColor,
                      ),
                    ),
                    SizedBox(height: 8.h),
                    Text(
                      'Sign in to your driver account',
                      style: TextStyle(
                        fontSize: 16.sp,
                        color: AppColors.greyColor,
                      ),
                    ),
                  ],
                ),
              ),

              SizedBox(height: 40.h),

              // Login form
              Obx(() => Column(
                    children: [
                      // Email field
                      TextFormField(
                        decoration: InputDecoration(
                          hintText: 'Email',
                          prefixIcon: Icon(Icons.email_outlined),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8.r),
                          ),
                          errorText: _controller.email.value.isNotEmpty &&
                                  !_controller.isEmailValid.value
                              ? 'Please enter a valid email'
                              : null,
                        ),
                        controller: _emailController,
                        onChanged: (value) =>
                            _controller.updateField('email', value),
                        keyboardType: TextInputType.emailAddress,
                      ),

                      SizedBox(height: 20.h),

                      // Password field
                      TextFormField(
                        decoration: InputDecoration(
                          hintText: 'Password',
                          prefixIcon: Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _isPasswordVisible
                                  ? Icons.visibility
                                  : Icons.visibility_off,
                              color: AppColors.primaryColor,
                            ),
                            onPressed: () {
                              setState(() {
                                _isPasswordVisible = !_isPasswordVisible;
                              });
                            },
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8.r),
                          ),
                          errorText: _controller.password.value.isNotEmpty &&
                                  !_controller.isPasswordValid.value
                              ? 'Password must be at least 6 characters'
                              : null,
                        ),
                        controller: _passwordController,
                        onChanged: (value) =>
                            _controller.updateField('password', value),
                        obscureText: !_isPasswordVisible,
                      ),

                      SizedBox(height: 30.h),

                      // Error message
                      if (_controller.error.value.isNotEmpty)
                        Container(
                          padding: EdgeInsets.all(12.w),
                          margin: EdgeInsets.only(bottom: 20.h),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(8.r),
                            border: Border.all(color: Colors.red.shade200),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.error_outline,
                                  color: Colors.red, size: 20.w),
                              SizedBox(width: 8.w),
                              Expanded(
                                child: Text(
                                  _controller.error.value,
                                  style: TextStyle(
                                    color: Colors.red.shade700,
                                    fontSize: 14.sp,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),

                      // Login button
                      Obx(() => CustomButton(
                            text: 'Login',
                            ontap: () {
                              if (_controller.isLoginFormValid &&
                                  !_controller.isLoading.value) {
                                _controller.login().then((success) {
                                  if (success) {
                                    Get.offAllNamed('/driver/home');
                                  }
                                });
                              }
                            },
                          )),

                      SizedBox(height: 20.h),

                      // Forgot password
                      TextButton(
                        onPressed: () {
                          Get.to(
                            ForgotPasswordPage(userType: 'driver'),
                            transition: Transition.cupertino,
                          );
                        },
                        child: Text(
                          'Forgot Password?',
                          style: TextStyle(
                            color: AppColors.primaryColor,
                            fontSize: 14.sp,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),

                      SizedBox(height: 30.h),

                      // Register link
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            "Don't have an account? ",
                            style: TextStyle(
                              color: AppColors.greyColor,
                              fontSize: 14.sp,
                            ),
                          ),
                          TextButton(
                            onPressed: () {
                              Get.to(
                                () => const DriverUnifiedSignupScreen(),
                                transition: Transition.rightToLeft,
                                duration: Duration(milliseconds: 300),
                                curve: Curves.easeInOut,
                              );
                            },
                            child: Text(
                              'Register',
                              style: TextStyle(
                                color: AppColors.primaryColor,
                                fontSize: 14.sp,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  )),
            ],
          ),
        ),
      ),
    );
  }
}
