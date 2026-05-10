import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:deliver_mee/src/feature/auth/sign_in/sign_in_page.dart';
import 'package:deliver_mee/src/feature/auth/upload_document/upload_document.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:pin_code_fields/pin_code_fields.dart';

class EmailVerifiedPage extends StatefulWidget {
  final int index;
  final String email;
  final String phoneNumber;
  const EmailVerifiedPage(
      {super.key,
      required this.index,
      required this.email,
      required this.phoneNumber});

  @override
  State<EmailVerifiedPage> createState() => _EmailVerifiedPageState();
}

class _EmailVerifiedPageState extends State<EmailVerifiedPage> {
  TextEditingController otpController = TextEditingController();
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      body: Padding(
        padding: EdgeInsets.all(15.h),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextWidget(
                text: widget.index == 0
                    ? 'Verification Phone'
                    : 'Verification Email',
                fontSize: 24.sp,
                color: AppColors.naveBlue,
                fontWeight: FontWeight.w600,
              ),
              TextWidget(
                textAlign: TextAlign.center,
                text: widget.index == 0
                    ? 'Please enter the code we just sent to Phone Number'
                    : 'Please enter the code we just sent to email',
                fontSize: 14.sp,
                color: AppColors.richTextColor,
                fontWeight: FontWeight.w400,
              ),
              TextWidget(
                textAlign: TextAlign.center,
                text: widget.index == 0 ? widget.phoneNumber : widget.email,
                fontSize: 14.sp,
                color: AppColors.greyTextColor,
                fontWeight: FontWeight.w500,
              ),
              SizedBox(
                height: 30.h,
              ),
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 28.w),
                child: PinCodeTextField(
                  appContext: context,
                  length: 4,
                  controller: otpController,
                  keyboardType: TextInputType.number,
                  animationType: AnimationType.fade,
                  pinTheme: PinTheme(
                    shape: PinCodeFieldShape.box,
                    borderRadius: BorderRadius.circular(8.r),
                    fieldHeight: 60.h,
                    fieldWidth: 50.w,
                    activeFillColor: AppColors.whiteColor,
                    inactiveColor: AppColors.richTextColor,
                    activeColor: AppColors.richTextColor,
                    selectedColor: AppColors.primaryColor,
                  ),
                  onChanged: (value) {
                    setState(() {});
                  },
                ),
              ),
              SizedBox(
                height: 15.h,
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  TextWidget(
                    text: 'If you didn’t receive a code?',
                    fontSize: 14.sp,
                    fontWeight: FontWeight.w500,
                    color: AppColors.richTextColor,
                  ),
                  InkWell(
                    onTap: () {},
                    child: TextWidget(
                      text: '  Resend',
                      fontSize: 14.sp,
                      fontWeight: FontWeight.w500,
                      color: AppColors.primaryColor,
                    ),
                  )
                ],
              ),
              SizedBox(
                height: 40.h,
              ),
              CustomButton(
                  text: 'Continue',
                  ontap: () {
                    if (otpController.text.length == 4) {
                      if (AuthController.to.selectedIndex.value == 0) {
                        Get.off(UploadDocumentPage(),
                            transition: Transition.cupertino);
                      } else {
                        Get.offAll(SignInPage(),
                            transition: Transition.cupertino);
                      }
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text('Please enter a valid OTP'),
                        backgroundColor: AppColors.redColor,
                      ));
                    }
                  })
            ],
          ),
        ),
      ),
    );
  }
}
