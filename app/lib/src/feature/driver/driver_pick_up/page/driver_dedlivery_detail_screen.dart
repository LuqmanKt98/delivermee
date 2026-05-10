import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/driver/driver_bottom_bar/pages/driver_bottom_bar_screen.dart';
import 'package:deliver_mee/src/feature/user/delivery/controller.dart';
import 'package:deliver_mee/src/feature/user/payment/payment.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';

class DriverDedliveryDetailScreen extends StatefulWidget {
  const DriverDedliveryDetailScreen({super.key});

  @override
  State<DriverDedliveryDetailScreen> createState() =>
      _DriverDedliveryDetailScreenState();
}

class _DriverDedliveryDetailScreenState
    extends State<DriverDedliveryDetailScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      appBar: CustomAppBar(text: "Schedule Delivery", leading: true),
      body: Padding(
        padding: EdgeInsets.all(16.w),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Address info
              locationSelectorRow(),
              SizedBox(height: 16.h),

              Row(
                children: [
                  _summaryBox("Total Item", "2"),
                  _summaryBox("Small", "12"),
                  _summaryBox("5.5", "LB"),
                ],
              ),

              SizedBox(height: 15.h),
              TextWidget(
                text: 'Delivery Proof',
                fontSize: 16.sp,
                fontWeight: FontWeight.w500,
                color: AppColors.greyTextColor,
              ),
              SizedBox(height: 15.h),

              // Images
              SizedBox(
                height: 140.h,
                child: Row(
                  children: [
                    Expanded(
                      child: _imageBox(
                        AppImages.boxone,
                      ),
                    ),
                    SizedBox(
                      width: 10.w,
                    ),
                    Expanded(child: _imageBox(AppImages.boxtwo)),
                  ],
                ),
              ),

              SizedBox(height: 16.h),
              TextWidget(
                text: 'Preference',
                fontSize: 16.sp,
                color: AppColors.greyTextColor,
                fontWeight: FontWeight.w500,
              ),
              SizedBox(
                height: 10.h,
              ),
              TextWidget(
                text:
                    'Leave at Residence/Location: Permission is granted for the driver to leave the package at the residence/location.',
                fontSize: 12.sp,
                fontWeight: FontWeight.w400,
                color: AppColors.greyTextColor,
              ),

              SizedBox(height: 10.h),

              TextWidget(
                text: "Extra Delivery Notes",
                fontSize: 14.sp,
                fontWeight: FontWeight.w500,
                color: AppColors.greyTextColor,
              ),
              SizedBox(height: 6.h),
              TextWidget(
                text: 'Call upon arrival.',
                fontSize: 12.sp,
                fontWeight: FontWeight.w400,
                color: AppColors.greyTextColor,
              ),

              SizedBox(height: 20.h),
              CustomContainer(
                color: AppColors.containerColor,
                borderRadius: 12.r,
                boxShadow: [
                  BoxShadow(
                      offset: Offset(0, 4),
                      blurRadius: 4,
                      color: AppColors.blackColor.withOpacity(.16))
                ],
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 10.h),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    TextWidget(
                      text: "Total Payment",
                      fontWeight: FontWeight.w600,
                      fontSize: 16.sp,
                    ),
                    TextWidget(
                      text: "\$ 28",
                      fontWeight: FontWeight.w500,
                      fontSize: 16.sp,
                    ),
                  ],
                ),
              ),
              SizedBox(height: 30.h),

              CustomButton(
                  text: "Go to Home",
                  ontap: () {
                    Get.off(DriverBottomBarScreen(),
                        transition: Transition.cupertino);
                  }),
            ],
          ),
        ),
      ),
    );
  }

  Widget _summaryBox(String label, String value) {
    return Expanded(
      child: Container(
        margin: EdgeInsets.symmetric(horizontal: 4.w),
        padding: EdgeInsets.symmetric(vertical: 8.h),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade400),
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          children: [
            TextWidget(
                text: "${label} ${value}",
                fontWeight: FontWeight.w400,
                fontSize: 14.sp),
          ],
        ),
      ),
    );
  }

  Widget _imageBox(String img) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(10.r),
        image: DecorationImage(
          fit: BoxFit.cover,
          image: AssetImage(
            img,
          ),
        ),
      ),
    );
  }

  Widget locationSelectorRow() {
    return Stack(
      alignment: Alignment.center,
      children: [
        Row(
          children: [
            Expanded(
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 10.h),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.all(Radius.circular(12.r)),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Row(
                  children: [
                    Icon(Icons.radio_button_checked,
                        color: AppColors.primaryColor, size: 18.sp),
                    SizedBox(width: 8.w),
                    Expanded(
                      child: TextWidget(
                        text: "234 Palm Oasis..",
                        fontSize: 14.sp,
                        fontWeight: FontWeight.w400,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(
              width: 15.w,
            ),
            Expanded(
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 10.h),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.all(Radius.circular(12.r)),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Row(
                  children: [
                    SvgPicture.asset(
                      AppIcons.locationIcon,
                      height: 15.h,
                      width: 15.w,
                    ),
                    SizedBox(width: 8.w),
                    Expanded(
                      child: TextWidget(
                        text: "Walt Whitman...",
                        fontSize: 14.sp,
                        fontWeight: FontWeight.w400,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        Container(
          height: 36.w,
          width: 36.w,
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.grey.shade300),
          ),
          child: Center(
            child: SvgPicture.asset(
              AppIcons.arrowleftrightIcon,
              height: 15.h,
              width: 15.w,
            ),
          ),
        ),
      ],
    );
  }
}
