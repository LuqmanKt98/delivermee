import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/dialog.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/user/payment/controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

class AddCardScreen extends StatefulWidget {
  const AddCardScreen({super.key});

  @override
  State<AddCardScreen> createState() => _AddCardScreenState();
}

class _AddCardScreenState extends State<AddCardScreen> {
  TextEditingController cardno = TextEditingController();
  TextEditingController cardname = TextEditingController();
  TextEditingController expiry = TextEditingController();
  TextEditingController cvv = TextEditingController();
  final _fomkey = GlobalKey<FormState>();
  final PaymentMethodController paymentController =
      Get.find<PaymentMethodController>();
  bool isAddingCard = false;

  /// Add card using the payment service
  Future<void> _addCard() async {
    if (!_fomkey.currentState!.validate()) return;

    try {
      setState(() {
        isAddingCard = true;
      });

      // Parse expiry date
      final expiryParts = expiry.text.split('/');
      if (expiryParts.length != 2) {
        Get.snackbar(
          'Error',
          'Please enter expiry date in MM/YYYY format',
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
        return;
      }

      final result = await paymentController.addPaymentMethod(
        cardNumber: cardno.text.replaceAll(' ', ''),
        expiryMonth: expiryParts[0],
        expiryYear: expiryParts[1],
        cvv: cvv.text,
        cardholderName: cardname.text,
      );

      if (result['success']) {
        Get.dialog(
          ConfirmationDialog(
            aspectRatio: 1 / 0.6,
            onYesBtnClick: () {
              Get.back(); // Close dialog
              Get.back(); // Go back to payment screen
            },
            subDescription:
                "Your payment method has been added successfully. You can use this for all your deliveries.",
            heading: "Added Successfully",
          ),
        );
      } else {
        Get.snackbar(
          'Error',
          result['error'] ?? 'Failed to add payment method',
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
      }
    } catch (e) {
      Get.snackbar(
        'Error',
        'An unexpected error occurred. Please try again.',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    } finally {
      setState(() {
        isAddingCard = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(text: "Add Card", leading: true),
      body: Padding(
        padding: EdgeInsets.all(16.w),
        child: Form(
          key: _fomkey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextWidget(
                  text: 'Card Number',
                  fontSize: 14.sp,
                  color: AppColors.blackColor,
                  fontWeight: FontWeight.w600,
                ),
                SizedBox(
                  height: 10.h,
                ),
                CustomTextFormField(
                  keyboardType: TextInputType.number,
                  controller: cardno,
                  validator: (val) {
                    if (val!.isEmpty) {
                      return 'Input is Required';
                    } else {
                      return null;
                    }
                  },
                  hint: '0000 0000 0000 0000',
                  suffixIcon: Icon(
                    Icons.credit_card_outlined,
                    size: 20.sp,
                    color: AppColors.hintTextColor,
                  ),
                ),
                SizedBox(
                  height: 10.h,
                ),
                TextWidget(
                  text: 'Card Holder Name',
                  fontSize: 14.sp,
                  color: AppColors.blackColor,
                  fontWeight: FontWeight.w600,
                ),
                SizedBox(
                  height: 10.h,
                ),
                CustomTextFormField(
                  controller: cardname,
                  validator: (val) {
                    if (val!.isEmpty) {
                      return 'Input is Required';
                    } else {
                      return null;
                    }
                  },
                  hint: 'ex.Jonathan Paul Ive',
                ),
                SizedBox(
                  height: 10.h,
                ),
                Row(
                  children: [
                    Expanded(
                      child: TextWidget(
                        text: 'Expiry Date',
                        fontSize: 14.sp,
                        color: AppColors.blackColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(
                      width: 15.w,
                    ),
                    Expanded(
                      child: TextWidget(
                        text: 'CVV',
                        fontSize: 14.sp,
                        color: AppColors.blackColor,
                        fontWeight: FontWeight.w600,
                      ),
                    )
                  ],
                ),
                SizedBox(
                  height: 10.h,
                ),
                Row(
                  children: [
                    Expanded(
                        child: CustomTextFormField(
                      hint: 'MM/YYYY',
                      controller: expiry,
                      validator: (val) {
                        if (val!.isEmpty) {
                          return 'Input is Required';
                        } else {
                          return null;
                        }
                      },
                    )),
                    SizedBox(
                      width: 15.w,
                    ),
                    Expanded(
                        child: CustomTextFormField(
                      hint: '3 - 4 digit',
                      controller: cvv,
                      validator: (val) {
                        if (val!.isEmpty) {
                          return 'Input is Required';
                        } else if (val.length != 3 && val.length != 4) {
                          return 'Max length is 3 or 4';
                        } else {
                          return null;
                        }
                      },
                    ))
                  ],
                ),
                SizedBox(height: 30.h),
                TextWidget(
                  text:
                      'Your personal data will be used to process your order, support your experience throughout this website, and for other purposes described in our privacy policy.',
                  fontSize: 10.sp,
                  fontWeight: FontWeight.w400,
                  color: Colors.black87,
                ),
                SizedBox(height: 20.h),
                Obx(() => CustomButton(
                      text: isAddingCard ? 'Adding Card...' : 'Add Card',
                      buttonColor:
                          isAddingCard ? Colors.grey : AppColors.primaryColor,
                      ontap: isAddingCard ? () {} : () => _addCard(),
                    )),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
