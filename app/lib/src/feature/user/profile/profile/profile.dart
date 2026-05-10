import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/role_selected/role_selected_page.dart';
import 'package:deliver_mee/src/feature/user/profile/customer_support/customer_support.dart';
import 'package:deliver_mee/src/feature/user/profile/edit_profile/edit_profile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class UserProfileScreen extends StatefulWidget {
  const UserProfileScreen({super.key});

  @override
  State<UserProfileScreen> createState() => _UserProfileScreenState();
}

class _UserProfileScreenState extends State<UserProfileScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(text: "User Profile", leading: false),
      body: Padding(
        padding: EdgeInsets.all(16.w),
        child: Container(
          height: ScreenUtil().screenHeight,
          width: ScreenUtil().screenWidth,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                height: 20.h,
              ),
              profieContainerWidget(
                icon: AppIcons.profileFillIcon,
                text: "Edit Profile",
                ontap: () {
                  Get.to(EditProfileScreen(), transition: Transition.cupertino);
                },
              ),
              SizedBox(
                height: 20.h,
              ),
              profieContainerWidget(
                icon: AppIcons.messageIcon,
                text: "Customer Support",
                ontap: () {
                  Get.to(CustomerSupportScreen(),
                      transition: Transition.cupertino);
                },
              ),
              SizedBox(
                height: 20.h,
              ),
              profieContainerWidget(
                icon: AppIcons.logoutIcon,
                text: "Logout",
                ontap: () async {
                  // Show confirmation dialog
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: Text('Logout'),
                      content: Text('Are you sure you want to logout?'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: Text('Cancel'),
                        ),
                        TextButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: Text('Logout', style: TextStyle(color: Colors.red)),
                        ),
                      ],
                    ),
                  );

                  if (confirmed == true) {
                    // Clear all user data
                    final prefs = await SharedPreferences.getInstance();
                    await prefs.clear();
                    
                    // Navigate to role selection
                    Get.offAll(RoleSelectedPage(), transition: Transition.cupertino);
                    
                    // Show success message
                    Get.snackbar(
                      'Logged Out',
                      'You have been successfully logged out',
                      snackPosition: SnackPosition.BOTTOM,
                      backgroundColor: Colors.green,
                      colorText: Colors.white,
                      duration: Duration(seconds: 2),
                    );
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget profieContainerWidget({
    required String icon,
    required String text,
    required VoidCallback ontap,
  }) {
    return CustomContainer(
      height: 55.h,
      onTap: ontap,
      width: double.infinity,
      color: AppColors.primaryColor.withOpacity(0.1),
      borderRadius: 100.r,
      child: Row(
        children: [
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 20.w),
            child: SvgPicture.asset(
              icon,
              color: Colors.black,
            ),
          ),
          TextWidget(
            text: text,
            fontSize: 15.sp,
            fontWeight: FontWeight.w500,
          ),
        ],
      ),
    );
  }
}
