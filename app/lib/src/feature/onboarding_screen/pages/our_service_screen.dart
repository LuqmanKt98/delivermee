import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/role_selected/role_selected_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

class OurServiceScreen extends StatelessWidget {
  OurServiceScreen({super.key});

  @override
  List<Color> colorsList = [
    Color(0xffDBFFF6),
    Color(0xffECE5FF),
    Color(0xffFFF5DC),
    Color(0xffF6FFE0),
    Color(0xffFFF3E5),
    Color(0xffE0E5FF),
    Color(0xffF5E5FF),
    Color(0xffFFFBD3),
    Color(0xffE8FFE5),
    Color(0xffFFEEE5),
  ];

  List<String> textList = [
    'Home Delivery',
    'College Moving',
    'Storage Moving',
    'Office Moving',
    'Furniture Delivery',
    'Marketplace Delivery',
    'Kijiji Delivery',
    'Appliance Delivery',
    'Junk Removal',
    'Donation Pick Up'
  ];
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      body: SingleChildScrollView(
        child: Padding(
          padding: EdgeInsets.all(15.h),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 40.h,
              ),
              TextWidget(
                text: 'Book a delivery for any moment',
                fontSize: 20.sp,
                fontWeight: FontWeight.w600,
              ),
              Row(
                children: [
                  TextWidget(
                    text: 'with',
                    fontSize: 20.sp,
                    fontWeight: FontWeight.w600,
                  ),
                  SizedBox(
                    width: 6.w,
                  ),
                  Image.asset(
                    AppImages.logoText,
                    height: 24.h,
                  )
                ],
              ),
              SizedBox(
                height: 20.h,
              ),
              GridView.builder(
                physics: NeverScrollableScrollPhysics(),
                shrinkWrap: true,
                itemCount: 10,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 10.w,
                    mainAxisSpacing: 10.h,
                    mainAxisExtent: 70.h),
                itemBuilder: (conxtext, index) => CustomContainer(
                  color: colorsList[index],
                  borderRadius: 10.r,
                  child: Center(
                    child: TextWidget(
                      text: textList[index],
                      color: AppColors.darkGreayTextColor,
                      fontSize: 12.sp,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
              SizedBox(
                height: 20.h,
              ),
              CustomButton(
                height: 80.h,
                fontSize: 18.sp,
                text: 'Continue',
                ontap: () {
                  Get.offAll(RoleSelectedPage(),
                      transition: Transition.cupertino);
                },
              ),
              SizedBox(
                height: 20.h,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
