import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:deliver_mee/src/feature/auth/sign_in/sign_in_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

class RoleSelectedPage extends StatelessWidget {
  const RoleSelectedPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      body: Padding(
        padding: EdgeInsets.all(15.h),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Spacer(),
            Center(
              child: Image.asset(
                AppImages.logoText,
                height: 32.h,
              ),
            ),
            Spacer(),
            TextWidget(
              text: 'Continue as',
              color: AppColors.primaryColor,
              fontWeight: FontWeight.w600,
              fontSize: 28.sp,
            ),
            SizedBox(
              height: 20.h,
            ),
            Column(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(2, (index) {
                return Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.h),
                  child: Obx(() {
                    return CustomButton(
                          height: 90.h,
                      text: index == 0 ? 'Driver' : 'Customer',
                      buttonColor:
                          AuthController.to.selectedIndex.value == index
                              ? AppColors.primaryColor
                              : AppColors.unSelectedPrimaryColor,
                      ontap: () {
                        Get.to(
                          SignInPage(),
                          transition: Transition.cupertino,
                        );
                        AuthController.to.setSelectedIndex(index);
                      },
                    );
                  }),
                );
              }),
            ),
            SizedBox(
              height: 60.h,
            )
          ],
        ),
      ),
    );
  }
}
