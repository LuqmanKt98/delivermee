import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/rating_dialog.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

Widget driverCancleDialogue({
  required int deliveryId,
  required void Function(String reason) onReasonSubmit,
}) {
  final reasonController = TextEditingController();

  return Center(
    child: RatingDialog(
      onYesBtnClick: () {},
      lastButton: SizedBox(),
      child: SingleChildScrollView(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
          Align(
            alignment: Alignment.topRight,
            child: GestureDetector(
              onTap: () {
                Get.back();
              },
              child: Icon(Icons.close),
            ),
          ),
          TextWidget(
            text: 'Are You Sure?',
            color: AppColors.greyTextColor,
            fontSize: 24.sp,
            fontWeight: FontWeight.w500,
          ),
          TextWidget(
            text: 'Once you cancel delivery you won\'t be able\nto redo it.',
            textAlign: TextAlign.center,
            fontSize: 11.sp,
            color: AppColors.blackColor,
            fontWeight: FontWeight.w400,
          ),
          SizedBox(height: 20.h),
          Row(
            children: [
              TextWidget(
                text: 'Reason for Cancellation',
                fontSize: 15.sp,
                fontWeight: FontWeight.w500,
                color: AppColors.blackColor,
              ),
              TextWidget(
                text: '*',
                color: AppColors.redColor,
                fontSize: 15.sp,
              ),
            ],
          ),
          SizedBox(height: 10.h),
          CustomTextFormField(
            controller: reasonController,
            validator: (validator) {},
            maxline: 5,
            hint: 'Add comment here',
          ),
          SizedBox(height: 20.h),
          CustomButton(
            text: 'Confirm',
            ontap: () {
              final reason = reasonController.text.trim();
              if (reason.isEmpty) {
                Get.snackbar(
                  'Required',
                  'Please provide a cancellation reason',
                  backgroundColor: Colors.orange,
                  colorText: Colors.white,
                );
                return;
              }
              onReasonSubmit(reason);
            },
          )
        ],
      ),
        ),
    ),
  );
}
