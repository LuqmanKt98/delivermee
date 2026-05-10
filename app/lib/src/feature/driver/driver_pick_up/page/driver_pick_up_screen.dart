import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/custom_text_form_field.dart';
import 'package:deliver_mee/src/common/utils/rating_dialog.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/auth/controller/auth_controller.dart';
import 'package:deliver_mee/src/feature/driver/driver_bottom_bar/driver_chat_screen.dart';
import 'package:deliver_mee/src/feature/driver/driver_bottom_bar/pages/driver_bottom_bar_screen.dart';
import 'package:deliver_mee/src/feature/driver/driver_pick_up/controller/driver_pick_up_controller.dart';
import 'package:deliver_mee/src/feature/driver/driver_pick_up/dialogue/driver_cancel_dialogue.dart';
import 'package:deliver_mee/src/feature/driver/driver_pick_up/dialogue/view_recepie_dialogue.dart';
import 'package:deliver_mee/src/feature/driver/driver_pick_up/page/driver_map_page.dart';
import 'package:deliver_mee/src/feature/user/confirm_delivery/controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';

class DriverPickUpScreen extends StatelessWidget {
  DriverPickUpScreen({super.key});
  final DriverPickUpController ctrl = Get.find<DriverPickUpController>();

  // Get delivery data from arguments
  Map<String, dynamic>? get deliveryData =>
      Get.arguments as Map<String, dynamic>?;
  Map<String, dynamic>? get delivery => deliveryData?['delivery'];
  Map<String, dynamic>? get customer => deliveryData?['customer'];
  Map<String, dynamic>? get nextSteps => deliveryData?['next_steps'];
  Map<String, dynamic>? get originalDeliveryData =>
      deliveryData?['original_delivery'];

  void _debugDeliveryData() {
    // Debug the received data
    print('🚚 ===== DRIVER PICKUP SCREEN DEBUG =====');
    print('🚚 Full delivery data received: $deliveryData');
    print('🚚 Delivery object: $delivery');
    print('🚚 Next steps: $nextSteps');
    print('🚚 Customer: $customer');
    print('🚚 Original delivery data: $originalDeliveryData');

    if (delivery != null) {
      print('🚚 Pickup address: ${delivery!['pickup_address']}');
      print('🚚 Dropoff address: ${delivery!['dropoff_address']}');
      print(
          '🚚 Pickup coordinates: ${delivery!['pickup_latitude']}, ${delivery!['pickup_longitude']}');
      print(
          '🚚 Dropoff coordinates: ${delivery!['dropoff_latitude']}, ${delivery!['dropoff_longitude']}');
    }

    if (nextSteps != null) {
      print('🚚 Next steps pickup: ${nextSteps!['pickup_location']}');
      print('🚚 Next steps dropoff: ${nextSteps!['dropoff_location']}');
    }

    if (originalDeliveryData != null) {
      print(
          '🚚 Original pickup address: ${originalDeliveryData!['pickup_address']}');
      print(
          '🚚 Original dropoff address: ${originalDeliveryData!['dropoff_address']}');
      print(
          '🚚 Original pickup coordinates: ${originalDeliveryData!['pickup_latitude']}, ${originalDeliveryData!['pickup_longitude']}');
      print(
          '🚚 Original dropoff coordinates: ${originalDeliveryData!['dropoff_latitude']}, ${originalDeliveryData!['dropoff_longitude']}');
    }
    print('🚚 ======================================');
  }

  String _formatScheduledDate(dynamic dateStr) {
    if (dateStr == null || dateStr.toString().isEmpty) return 'N/A';
    try {
      final dateOnly = dateStr.toString().split('T')[0];
      final dateTime = DateTime.parse(dateOnly);
      final weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      final weekday = weekdays[dateTime.weekday - 1];
      final month = months[dateTime.month - 1];
      return '$weekday, ${dateTime.day} $month';
    } catch (e) {
      return dateStr.toString();
    }
  }

  String _formatTimeSlot(dynamic timeSlot) {
    if (timeSlot == null || timeSlot.toString().isEmpty) return 'N/A';
    try {
      final parts = timeSlot.toString().split('-');
      if (parts.length == 2) {
        String formatTime(String time24) {
          final hour = int.parse(time24.split(':')[0]);
          if (hour == 0) return '12:00 AM';
          if (hour < 12) return '$hour:00 AM';
          if (hour == 12) return '12:00 PM';
          return '${hour - 12}:00 PM';
        }
        return '${formatTime(parts[0])} - ${formatTime(parts[1])}';
      }
      return timeSlot.toString();
    } catch (e) {
      return timeSlot.toString();
    }
  }

  int _getStepFromDeliveryStatus(String? status) {
    if (status == null) return 0;
    switch (status.toLowerCase()) {
      case 'assigned':
      case 'accepted':
        return 0;
      case 'picked_up':
        return 1;
      case 'in_transit':
        return 2;
      case 'delivered':
        return 3;
      default:
        return 0;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Debug the delivery data
    _debugDeliveryData();

    // Initialize current step based on delivery status
    final currentStatus = delivery?['status'] as String?;
    final initialStep = _getStepFromDeliveryStatus(currentStatus);
    final confirmController = Get.find<ConfirmDeliveryController>();
    confirmController.initializeStep(initialStep);

    return Scaffold(
      body: Stack(
        children: [
          SafeArea(
            child: Container(
              height: 450.h,
              width: double.infinity,
              decoration: BoxDecoration(
                image: DecorationImage(
                  image: AssetImage(AppImages.confirmdeliverymapimg),
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 20.h),
              width: double.infinity,
              height: 450.h,
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    offset: Offset(0, -4),
                    blurRadius: 10.r,
                    spreadRadius: 2.r,
                  ),
                ],
                borderRadius: BorderRadius.vertical(top: Radius.circular(16.r)),
              ),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Container(
                        width: 57.w,
                        height: 5.h,
                        decoration: BoxDecoration(
                          color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(8.r),
                        ),
                      ),
                    ),
                    SizedBox(height: 24.h),
                    Row(
                      children: [
                        TextWidget(
                          text: nextSteps?['estimated_pickup_time'] ??
                              '20 mins Apart',
                          fontSize: 20.sp,
                          fontWeight: FontWeight.w600,
                        ),
                        Spacer(),
                        TextWidget(
                          text:
                              '\$${delivery?['estimated_cost']?.toStringAsFixed(2) ?? '28'}',
                          fontSize: 20.sp,
                          fontWeight: FontWeight.w600,
                        ),
                      ],
                    ),
                    // Display scheduled date and time slot if available
                    if (delivery?['scheduled_date'] != null || delivery?['time_slot'] != null) ...[
                      SizedBox(height: 12.h),
                      Container(
                        padding: EdgeInsets.all(12.w),
                        decoration: BoxDecoration(
                          color: Color(0xFFF0F7FF),
                          borderRadius: BorderRadius.circular(10.r),
                          border: Border.all(
                            color: AppColors.primaryColor.withOpacity(0.3),
                            width: 1.5,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (delivery?['scheduled_date'] != null) ...[
                              Row(
                                children: [
                                  Icon(
                                    Icons.calendar_today,
                                    size: 16.sp,
                                    color: AppColors.primaryColor,
                                  ),
                                  SizedBox(width: 8.w),
                                  TextWidget(
                                    text: 'Scheduled for: ${_formatScheduledDate(delivery?['scheduled_date'])}',
                                    fontSize: 12.sp,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.primaryColor,
                                  ),
                                ],
                              ),
                            ],
                            if (delivery?['time_slot'] != null) ...[
                              if (delivery?['scheduled_date'] != null) SizedBox(height: 6.h),
                              Row(
                                children: [
                                  Icon(
                                    Icons.access_time,
                                    size: 16.sp,
                                    color: AppColors.primaryColor,
                                  ),
                                  SizedBox(width: 8.w),
                                  TextWidget(
                                    text: 'Time Slot: ${_formatTimeSlot(delivery?['time_slot'])}',
                                    fontSize: 12.sp,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.primaryColor,
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                    buildPickupDetails(context),
                    SizedBox(height: 10.h),
                    Row(
                      children: [
                        Expanded(
                          child: CustomButton(
                            buttonColor: AppColors.unSelectedPrimaryColor,
                            text: 'Cancel Delivery',
                            ontap: () {
                              final deliveryId = delivery?['id'] as int?;
                              if (deliveryId == null) {
                                Get.snackbar(
                                  'Error',
                                  'Delivery ID not found',
                                  backgroundColor: Colors.red,
                                  colorText: Colors.white,
                                );
                                return;
                              }

                              Get.dialog(driverCancleDialogue(
                                deliveryId: deliveryId,
                                onReasonSubmit: (reason) {
                                  Get.back();
                                  _showCancellationReviewDialog(
                                    deliveryId,
                                    reason,
                                  );
                                },
                              ));
                            },
                          ),
                        ),
                        SizedBox(
                          width: 10.w,
                        ),
                        Expanded(
                          child: CustomButton(
                            text: 'See on Map',
                            ontap: () {
                              Get.to(() => DriverMapPage(),
                                  transition: Transition.cupertino);
                            },
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Align(
                alignment: Alignment.topLeft,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    GestureDetector(
                      onTap: () {
                        Get.back();
                      },
                      child: Image.asset(
                        AppImages.logo,
                        height: 50.h,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        ],
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

  void _showCancellationReviewDialog(int deliveryId, String reason) {
    final reviewController = TextEditingController();

    Get.dialog(
      Center(
        child: RatingDialog(
          onYesBtnClick: () {
            ctrl.cancelDelivery(
              deliveryId: deliveryId,
              cancellationReason: reason,
              rating: null,
              review: reviewController.text.trim(),
            );
          },
          tipBool: false,
          topText: 'Cancel Delivery',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextWidget(
                text: 'Please provide your feedback',
                fontSize: 12.sp,
                color: Colors.grey,
              ),
              SizedBox(height: 20.h),
              TextField(
                controller: reviewController,
                maxLines: 4,
                decoration: InputDecoration(
                  hintText: 'Additional comments (optional)',
                  hintStyle: TextStyle(
                    color: AppColors.hintTextColor,
                    fontSize: 14.sp,
                  ),
                  filled: true,
                  fillColor: const Color(0xFFF4F4F4),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12.r),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ],
          ),
          lastButton: SizedBox(
            height: 48,
            child: Row(
              children: [
                Expanded(
                  child: CustomButton(
                    text: 'Back',
                    buttonColor: AppColors.unSelectedPrimaryColor,
                    fontSize: 13.sp,
                    ontap: () {
                      Navigator.of(Get.context!).pop();
                    },
                  ),
                ),
                SizedBox(width: 10.w),
                Expanded(
                  child: Obx(() => CustomButton(
                    text: ctrl.isLoading.value ? 'Cancelling...' : 'Submit',
                    buttonColor: ctrl.isLoading.value
                        ? AppColors.greyTextColor.withOpacity(0.4)
                        : AppColors.primaryColor,
                    fontSize: 13.sp,
                    ontap: () {
                      if (!ctrl.isLoading.value) {
                        ctrl.cancelDelivery(
                          deliveryId: deliveryId,
                          cancellationReason: reason,
                          rating: null,
                          review: reviewController.text.trim(),
                        );
                      }
                    },
                  )),
                ),
              ],
            ),
          ),
        ),
      ),
      barrierDismissible: false,
    );
  }

  Widget buildPickupDetails(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(height: 10.h),
        StepProgressBar(deliveryData: delivery),
        SizedBox(height: 10.h),
        Row(
          children: [
            _summaryBox("Total Item", "${delivery?['item_count'] ?? '2'}"),
            _summaryBox("Package", "${delivery?['package_size'] ?? 'Small'}"),
            _summaryBox(
                "${delivery?['weight']?.toStringAsFixed(1) ?? '5.5'}", "LB"),
          ],
        ),
        SizedBox(height: 15.h),
        TextWidget(
          text: 'Preference',
          fontSize: 15.sp,
          fontWeight: FontWeight.w600,
          color: AppColors.darkGreayTextColor,
        ),
        SizedBox(height: 10.h),
        TextWidget(
          text: delivery?['delivery_type'] == 'signature_required'
              ? 'Signature Required: Customer must sign for delivery.'
              : 'Leave at Residence/Location: Permission is granted for the driver to leave the package at the residence/location.',
          fontSize: 12.sp,
          color: AppColors.greyTextColor,
        ),
        SizedBox(
          height: 10.h,
        ),
        TextWidget(
          text: 'Extra Delivery Notes',
          fontSize: 15.sp,
          fontWeight: FontWeight.w600,
          color: AppColors.darkGreayTextColor,
        ),
        SizedBox(
          height: 10.h,
        ),
        TextWidget(
          text: delivery?['special_instructions'] ?? 'Call upon arrival.',
          fontSize: 12.sp,
          color: AppColors.greyTextColor,
        ),
        SizedBox(
          height: 10.h,
        ),
        CustomTextFormField(
          controller: TextEditingController(),
          borderRadius: 100.r,
          validator: (val) {
            return null;
          },
          hint: 'Any Query',
          suffixIcon: CustomContainer(
            width: 100.w,
            color: AppColors.textfieldColor,
            borderRadius: 100.r,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                GestureDetector(
                  onTap: () {
                    Get.to(DriverChatScreen(),
                        transition: Transition.cupertino);
                  },
                  child: CircleAvatar(
                    backgroundColor: Colors.transparent,
                    child: SvgPicture.asset(AppIcons.messageIcon),
                  ),
                ),
                GestureDetector(
                  onTap: () async {
                    // Get customer phone number
                    final customerPhone = customer?['phone'] ?? delivery?['customer']?['phone'];
                    
                    if (customerPhone != null && customerPhone.toString().isNotEmpty) {
                      final phoneUrl = 'tel:$customerPhone';
                      print('📞 Calling customer: $phoneUrl');
                      
                      try {
                        final uri = Uri.parse(phoneUrl);
                        if (await canLaunchUrl(uri)) {
                          await launchUrl(uri);
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Could not open phone dialer'),
                              backgroundColor: Colors.red,
                            ),
                          );
                        }
                      } catch (e) {
                        print('❌ Error launching phone: $e');
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Error: $e'),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    } else {
                      print('⚠️ Customer phone not available');
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Customer phone number not available'),
                          backgroundColor: Colors.orange,
                        ),
                      );
                    }
                  },
                  child: CircleAvatar(
                    backgroundColor: Colors.transparent,
                    child: SvgPicture.asset(
                      AppIcons.phoneprofileIcon,
                      height: 27.h,
                      color: AppColors.blackColor,
                    ),
                  ),
                )
              ],
            ),
          ),
        ),
        SizedBox(
          height: 10.h,
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: RichText(
                textAlign: TextAlign.start,
                text: TextSpan(
                  text: 'Take picture of your delivery or upload ',
                  style: TextStyle(
                    fontSize: 12.sp,
                    fontWeight: FontWeight.w500,
                    color: AppColors.blackColor,
                  ),
                  children: [
                    TextSpan(
                      text: '*',
                      style: TextStyle(
                        color: AppColors.redColor,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            GetBuilder<DriverPickUpController>(
              id: 'pickfile',
              builder: (scontext) {
                return GestureDetector(
                  onTap: () async {
                    await ctrl.pickFile();
                  },
                  child: ctrl.pickedFilePath != null
                      ? Container(
                          width: 35.w,
                          height: 35.h,
                          decoration: BoxDecoration(
                            color: Colors.grey.shade200,
                            borderRadius: BorderRadius.circular(10.r),
                          ),
                          child: Center(
                            child: Padding(
                              padding: EdgeInsets.only(bottom: 10.h),
                              child: TextWidget(
                                text: '...',
                                color: AppColors.primaryColor,
                              ),
                            ),
                          ),
                        )
                      : CustomContainer(
                          width: 39.w,
                          height: 30.h,
                          borderRadius: 6.r,
                          color: Color(0xffe3e3e3),
                          child: Padding(
                            padding: EdgeInsets.all(2.0),
                            child: SvgPicture.asset(AppIcons.fileUploadIcon),
                          ),
                        ),
                );
              },
            ),
            SizedBox(width: 10.w),
            GetBuilder<DriverPickUpController>(
              id: 'selecteImage',
              builder: (scontext) {
                return GestureDetector(
                  onTap: () async {
                    await ctrl.pickImage();
                  },
                  child: ctrl.selectedImage != null
                      ? Container(
                          width: 35.w,
                          height: 35.h,
                          decoration: BoxDecoration(
                            color: Colors.grey.shade200,
                            borderRadius: BorderRadius.circular(10.r),
                          ),
                          child: Center(
                            child: Padding(
                              padding: EdgeInsets.only(bottom: 10.h),
                              child: TextWidget(
                                text: '...',
                                color: AppColors.primaryColor,
                              ),
                            ),
                          ),
                        )
                      : CustomContainer(
                          onTap: () async {
                            await DriverPickUpController.to.pickImage();
                          },
                          width: 39.w,
                          height: 30.h,
                          borderRadius: 6.r,
                          color: Color(0xffe3e3e3),
                          child: Padding(
                            padding: EdgeInsets.all(2.0),
                            child: SvgPicture.asset(AppIcons.cameraIcon),
                          ),
                        ),
                );
              },
            ),
          ],
        )
      ],
    );
  }
}

class StepProgressBar extends StatelessWidget {
  final Map<String, dynamic>? deliveryData;

  StepProgressBar({Key? key, this.deliveryData}) : super(key: key);

  final List<String> assets = [
    AppIcons.oneIcon,
    AppIcons.twoIcon,
    AppIcons.threeIcon,
    AppIcons.fourIcon,
  ];
  @override
  Widget build(BuildContext context) {
    final controller = Get.find<ConfirmDeliveryController>();
    final ctrl = Get.find<DriverPickUpController>();

    return Container(
      height: 60.h,
      child: Stack(
        alignment: Alignment.centerLeft,
        children: [
          // BASE LINE
          Positioned(
            left: 40.w,
            right: 40.w,
            child: Container(
              height: 2.h,
              color: Colors.grey.shade300,
            ),
          ),
          // ANIMATED BLACK LINE
          Positioned(
            left: 40.w,
            right: 40.w,
            child: AnimatedBuilder(
              animation: controller.animationController,
              builder: (_, __) {
                return FractionallySizedBox(
                  widthFactor: controller.progressAnimation.value,
                  alignment: Alignment.centerLeft,
                  child: Container(
                    height: 2.h,
                    color: Colors.black,
                  ),
                );
              },
            ),
          ),
          // STEP ICONS
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: List.generate(4, (index) {
              return Obx(() {
                bool isActive = controller.currentStep.value >= index;
                return GestureDetector(
                  onTap: () async {
                    // Get delivery ID from the delivery data
                    final deliveryId = deliveryData?['id'];
                    if (deliveryId == null) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text('Delivery ID not found'),
                        backgroundColor: AppColors.redColor,
                      ));
                      return;
                    }

                    if (ctrl.selectedImage == null &&
                        ctrl.pickedFilePath == null &&
                        (index == 3)) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text('Image is Required'),
                        backgroundColor: AppColors.redColor,
                      ));
                    } else {
                      controller.currentStep.value = index;
                      controller.animateToStep(index);

                      // Call appropriate API based on step
                      switch (index) {
                        case 0: // Box type icon - Pickup
                          await ctrl.pickupDelivery(deliveryId);
                          break;
                        case 1: // Car type icon - Start Transit
                          await ctrl.startTransitDelivery(deliveryId);
                          break;
                        case 2: // Third step - could be additional action if needed
                          // Add any additional logic here if needed
                          break;
                        case 3: // Tick mark - Complete delivery
                          await ctrl.completeDelivery(deliveryId);
                          // After completion, return to driver home without showing
                          // "Order Delivered" or "Review Customer" dialogs.
                          Get.offAll(DriverBottomBarScreen(),
                              transition: Transition.cupertino);
                          break;
                      }
                    }
                  },
                  child: Obx(
                    () => ctrl.isLoading.value &&
                            ((index == 0 &&
                                    controller.currentStep.value == 0) ||
                                (index == 1 &&
                                    controller.currentStep.value == 1) ||
                                (index == 3 &&
                                    controller.currentStep.value == 3))
                        ? Container(
                            height: 35.h,
                            width: 35.w,
                            padding: EdgeInsets.all(6.r),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.blue,
                              border: Border.all(
                                color: Colors.blue,
                                width: 1,
                              ),
                            ),
                            child: Center(
                              child: SizedBox(
                                height: 15.h,
                                width: 15.w,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                      Colors.white),
                                ),
                              ),
                            ),
                          )
                        : Container(
                            height: 35.h,
                            width: 35.w,
                            padding: EdgeInsets.all(6.r),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isActive ? Colors.black : Colors.white,
                              border: Border.all(
                                color: isActive
                                    ? Colors.black
                                    : Colors.grey.shade400,
                                width: 1,
                              ),
                            ),
                            child: SvgPicture.asset(
                              assets[index],
                              color: isActive ? Colors.white : Colors.grey,
                              height: 25.h,
                              width: 25.w,
                            ),
                          ),
                  ),
                );
              });
            }),
          ),
        ],
      ),
    );
  }
}
