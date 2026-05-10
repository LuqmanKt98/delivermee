import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/role_selected/role_selected_page.dart';
import 'package:deliver_mee/src/feature/driver/driver_profile/pages/driver_customer_support.dart';
import 'package:deliver_mee/src/feature/driver/driver_profile/pages/driver_edit_profile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';

class DriverProfilePage extends StatefulWidget {
  const DriverProfilePage({super.key});

  @override
  State<DriverProfilePage> createState() => _DriverProfilePageState();
}

class _DriverProfilePageState extends State<DriverProfilePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(text: "Driver Profile", leading: false),
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
                  Get.to(DriverEditProfile(), transition: Transition.cupertino);
                },
              ),
              SizedBox(
                height: 20.h,
              ),
              profieContainerWidget(
                icon: AppIcons.messageIcon,
                text: "Customer Support",
                ontap: () {
                  Get.to(DriverCustomerSupport(),
                      transition: Transition.cupertino);
                },
              ),
              SizedBox(
                height: 20.h,
              ),
              profieContainerWidget(
                icon: AppIcons.logoutIcon,
                text: "Logout",
                ontap: () {
                  Get.offAll(RoleSelectedPage(),
                      transition: Transition.cupertino);
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
