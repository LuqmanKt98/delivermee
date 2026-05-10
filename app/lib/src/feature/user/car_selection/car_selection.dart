import 'dart:math';

import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/user/bottom_bar/controller/bottom_bar_controller.dart';
import 'package:deliver_mee/src/feature/user/car_selection/controller.dart';
import 'package:deliver_mee/src/feature/user/car_selection/weight_lb_bottom_sheet.dart';
import 'package:deliver_mee/src/feature/user/car_selection/schedule_delivery_dialog.dart';
import 'package:deliver_mee/src/feature/user/home/controller/controller.dart';
import 'package:deliver_mee/src/feature/user/search/search.dart';
import 'package:deliver_mee/src/feature/user/payment/payment.dart';
import 'package:deliver_mee/src/models/car_model.dart';
import 'package:dotted_line/dotted_line.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';

class CarSelectionScreen extends StatefulWidget {
  final CarModel model;
  CarSelectionScreen({super.key, required this.model});

  @override
  State<CarSelectionScreen> createState() => _CarSelectionScreenState();
}

class _CarSelectionScreenState extends State<CarSelectionScreen> {
  @override
  void initState() {
    super.initState();
    // Calculate distance and time when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final CarController ctrl = Get.find<CarController>();
      final HomeController homeController = Get.find<HomeController>();

      // Calculate initial distance and time
      ctrl.calculateDistanceAndTime();

      // Listen to vehicle type changes and recalculate
      homeController.selectedVehicleType.listen((_) {
        ctrl.calculateDistanceAndTime();
      });

      // Listen to location changes and recalculate
      homeController.fromlocation.listen((_) {
        ctrl.calculateDistanceAndTime();
      });
      homeController.tolocation.listen((_) {
        ctrl.calculateDistanceAndTime();
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final CarController ctrl = Get.find<CarController>();
    final HomeController homectrl = Get.find<HomeController>();

    return Scaffold(
      // resizeToAvoidBottomInset: false,
      body: Stack(
        children: [
          // Map Section (fake map for demo)
          Container(
            height: 450.h,
            width: double.infinity,
            decoration: BoxDecoration(
              image: DecorationImage(
                image: AssetImage(AppImages.mapimage),
                fit: BoxFit.cover,
              ),
            ),
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Align(
                  alignment: Alignment.topLeft,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      GestureDetector(
                        onTap: () {
                          if (ctrl.iscontinuetab.value) {
                            ctrl.iscontinuetab.value = false;
                          } else {
                            Get.back();
                          }
                        },
                        child: Container(
                          height: 35.h,
                          width: 35.w,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white,
                            border: Border.all(
                              color: const Color(0xffC9C9C9),
                            ),
                          ),
                          child:
                              const Icon(Icons.arrow_back, color: Colors.black),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Bottom Sheet
          Align(
            alignment: Alignment.bottomCenter,
            child: Obx(
              () => Container(
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 20.h),
                width: double.infinity,
                height: ctrl.iscontinuetab.value ? null : 450.h,
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
                  borderRadius:
                      BorderRadius.vertical(top: Radius.circular(16.r)),
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    mainAxisSize: MainAxisSize.min,
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
                      SizedBox(
                        height: 80.h,
                        child: Obx(
                          () => Row(
                            // mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: List.generate(
                              ctrl.carslist.length,
                              (index) => _buildServiceItem(
                                  ctrl.carslist[index].image!,
                                  ctrl.carslist[index].name!, () {
                                ctrl.selectedindex.value = index;

                                // Update home controller with selected service type
                                final homeController =
                                    Get.find<HomeController>();
                                final selectedService = ctrl.carslist[index];

                                // Map service name to vehicle type and delivery type
                                String vehicleType = '';
                                String deliveryType = '';

                                switch (selectedService.name!.toLowerCase()) {
                                  case 'cargo van':
                                    vehicleType = 'cargo_van';
                                    deliveryType = 'cargo';
                                    break;
                                  case 'pickup truck':
                                    vehicleType = 'pickup_truck';
                                    deliveryType = 'pickup';
                                    break;
                                  default:
                                    vehicleType = 'cargo_van';
                                    deliveryType = 'cargo';
                                }

                                homeController.setVehicleType(vehicleType);
                                homeController.setDeliveryType(deliveryType);
                              }, index, ctrl),
                            ),
                          ),
                        ),
                      ),
                      SizedBox(
                        height: 20.h,
                      ),
                      ctrl.iscontinuetab.value
                          ? Column(
                              children: [
                                Row(
                                  children: [
                                    buildTimelineItem(),
                                    SizedBox(
                                      width: 10.w,
                                    ),
                                    Obx(
                                      () => locationCard(
                                          from: homectrl.fromlocation.value,
                                          to: homectrl.tolocation.value),
                                    ),
                                  ],
                                ),
                              ],
                            )
                          : SizedBox(),
                      ctrl.iscontinuetab.value
                          ? Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  height: 20.h,
                                ),
                                Row(
                                  children: [
                                    _buildServiceItem(
                                        ctrl.carslist[ctrl.selectedindex.value]
                                            .image!,
                                        ctrl.carslist[ctrl.selectedindex.value]
                                            .name!, () {
                                      ctrl.selectedindex.value =
                                          ctrl.selectedindex.value;
                                    }, 100, ctrl),
                                    SizedBox(
                                      width: 30.w,
                                    ),
                                    Obx(() => Column(
                                          children: [
                                            TextWidget(
                                              text: "DISTANCE",
                                              fontSize: 13.sp,
                                              fontWeight: FontWeight.w400,
                                            ),
                                            TextWidget(
                                              text: ctrl.isCalculatingDistance
                                                      .value
                                                  ? "Calculating..."
                                                  : ctrl.formattedDistance,
                                              fontSize: 15.sp,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ],
                                        )),
                                    SizedBox(
                                      width: 30.w,
                                    ),
                                    Obx(() => Column(
                                          children: [
                                            TextWidget(
                                              text: "TIME",
                                              fontSize: 13.sp,
                                              fontWeight: FontWeight.w400,
                                            ),
                                            TextWidget(
                                              text: ctrl.isCalculatingDistance
                                                      .value
                                                  ? "Calculating..."
                                                  : ctrl.formattedTime,
                                              fontSize: 15.sp,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ],
                                        )),
                                  ],
                                ),
                                SizedBox(
                                  height: 10.h,
                                ),
                                TextWidget(
                                  text: "Select Item Size",
                                  fontSize: 16.sp,
                                  fontWeight: FontWeight.w600,
                                ),
                                SizedBox(
                                  height: 10.h,
                                ),

                                // Size selection
                                Obx(() => Wrap(
                                      spacing: 8.w,
                                      children: List.generate(ctrl.sizes.length,
                                          (index) {
                                        bool isSelected =
                                            ctrl.selectedSize.value == index;
                                        return GestureDetector(
                                          onTap: () => ctrl.selectSize(index),
                                          child: Container(
                                            margin: EdgeInsets.symmetric(
                                                vertical: 4.h),
                                            padding: EdgeInsets.symmetric(
                                                vertical: 8.h, horizontal: 8.w),
                                            decoration: BoxDecoration(
                                              borderRadius:
                                                  BorderRadius.circular(10.r),
                                              border: Border.all(
                                                color: isSelected
                                                    ? AppColors.primaryColor
                                                    : Colors.grey,
                                                width: 1,
                                              ),
                                              color: isSelected
                                                  ? AppColors.primaryColor
                                                      .withOpacity(0.1)
                                                  : Colors.white,
                                            ),
                                            child: TextWidget(
                                              text: ctrl.sizes[index],
                                              fontWeight: FontWeight.w500,
                                              textAlign: TextAlign.center,
                                              fontSize: 14.sp,
                                              color: isSelected
                                                  ? AppColors.primaryColor
                                                  : Colors.black,
                                            ),
                                          ),
                                        );
                                      }),
                                    )),
                                SizedBox(height: 10.h),

                                Obx(() => Row(
                                      children: [
                                        TextWidget(
                                            text: "Items Count",
                                            fontWeight: FontWeight.w500,
                                            fontSize: 16.sp),
                                        Spacer(),
                                        _iconButton(() => ctrl.decrementItem(),
                                            Icons.remove),
                                        Padding(
                                          padding: EdgeInsets.symmetric(
                                              horizontal: 16.w),
                                          child: TextWidget(
                                              text: ctrl.itemCount.value
                                                  .toString(),
                                              fontSize: 16),
                                        ),
                                        _iconButton(() => ctrl.incrementItem(),
                                            Icons.add),
                                      ],
                                    )),
                                SizedBox(height: 10.h),

                                GestureDetector(
                                  onTap: () {
                                    weightPickerBottomSheet(
                                      context,
                                      initialWeight:
                                          BottomBarController.to.copyText.value,
                                      onWeightPicked: (pickedValue) {
                                        BottomBarController.to.selectedText
                                            .value = pickedValue;
                                      },
                                    );
                                  },
                                  child: CustomContainer(
                                    width: double.infinity,
                                    padding:
                                        EdgeInsets.symmetric(vertical: 2.h),
                                    child: Row(
                                      children: [
                                        TextWidget(
                                          text: "Weight of item",
                                          fontWeight: FontWeight.w500,
                                          fontSize: 16.sp,
                                        ),
                                        const Spacer(),
                                        Obx(() {
                                          return TextWidget(
                                            text: BottomBarController.to
                                                    .selectedText.value.isEmpty
                                                ? '1lb'
                                                : BottomBarController
                                                    .to.selectedText.value,
                                          );
                                        }),
                                      ],
                                    ),
                                  ),
                                ),
                                SizedBox(height: 20.h),

                                // Upload photo section
                                Row(
                                  // crossAxisAlignment:
                                  //     CrossAxisAlignment.start,
                                  // mainAxisAlignment: MainAxisAlignment.start,
                                  children: [
                                    // Wrapping long text in Flexible to allow wrapping or shrinking
                                    Expanded(
                                      child: RichText(
                                        textAlign: TextAlign.start,
                                        text: TextSpan(
                                          text:
                                              'Take picture of your delivery or upload ',
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
                                    // Upload file button
                                    GetBuilder<CarController>(
                                      id: 'pickfile',
                                      builder: (scontext) {
                                        return GestureDetector(
                                          onTap: () async =>
                                              await ctrl.pickFile(),
                                          child: ctrl.pickedFilePath != null
                                              ? _previewBox()
                                              : _imageButton(
                                                  ctrl.pickFile, Icons.upload),
                                        );
                                      },
                                    ),

                                    SizedBox(width: 8.w),

                                    // Upload image button
                                    GetBuilder<CarController>(
                                      id: 'selecteImage',
                                      builder: (scontext) {
                                        return GestureDetector(
                                          onTap: () async =>
                                              await ctrl.pickImage(),
                                          child: ctrl.selectedImage != null
                                              ? _previewBox()
                                              : _imageButton(ctrl.pickImage,
                                                  Icons.camera_alt),
                                        );
                                      },
                                    ),
                                  ],
                                ),
                              ],
                            )
                          : Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Obx(
                                  () => TextWidget(
                                    text: homectrl
                                        .carslist[ctrl.selectedindex.value]
                                        .name!,
                                    fontSize: 16.sp,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Obx(
                                  () => _buildCargoVanCard(homectrl
                                      .carslist[ctrl.selectedindex.value]),
                                ),
                              ],
                            ),
                      // Spacer(),
                      SizedBox(
                        height: 30.h,
                      ),
                      !ctrl.iscontinuetab.value
                          ? CustomButton(
                              text: 'Continue',
                              ontap: () {
                                ctrl.iscontinuetab.value = true;
                              },
                            )
                          : Row(
                              children: [
                                // Removed light background "Schedule" button - keeping only "Schedule Delivery" button
                                Expanded(
                                  child: CustomButton(
                                    text: 'Schedule Delivery',
                                    ontap: () async {
                                      if (ctrl.selectedImage != null ||
                                          ctrl.pickedFilePath != null) {
                                        // Show schedule dialog first
                                        showDialog(
                                          context: context,
                                          builder: (context) =>
                                              ScheduleDeliveryDialog(
                                            onScheduled: (DateTime date,
                                                String timeSlot) {
                                              // Use post-frame callback to avoid setState during build error
                                              WidgetsBinding.instance
                                                  .addPostFrameCallback(
                                                      (_) async {
                                                // Transfer car selection data to home controller
                                                final homeController =
                                                    Get.find<HomeController>();

                                                // Get selected service info
                                                final selectedService = ctrl
                                                        .carslist[
                                                    ctrl.selectedindex.value];

                                                // Set item details from car selection
                                                final packageSize = ctrl.sizes[
                                                        ctrl.selectedSize.value]
                                                    .split('\n')[0]
                                                    .toLowerCase();

                                                // Get weight from BottomBarController or fallback to car controller
                                                String weightText =
                                                    BottomBarController
                                                        .to.selectedText.value;
                                                if (weightText.isEmpty) {
                                                  weightText =
                                                      '${ctrl.itemWeight.value}lb';
                                                }

                                                // Parse weight (remove 'lb' and convert to double)
                                                final weight = double.tryParse(
                                                        weightText
                                                            .replaceAll(
                                                                'lb', '')
                                                            .trim()) ??
                                                    ctrl.itemWeight.value
                                                        .toDouble();
                                                final itemCount =
                                                    ctrl.itemCount.value;

                                                homeController.setItemDetails(
                                                  itemCount: itemCount,
                                                  weight: weight,
                                                  packageSize: packageSize,
                                                );

                                                // Set default item name if not set
                                                if (homeController
                                                    .itemName.value.isEmpty) {
                                                  homeController.setItemInfo(
                                                    itemName:
                                                        'Delivery for ${selectedService.name}',
                                                    itemDescription:
                                                        'Delivery via ${selectedService.name}',
                                                  );
                                                }

                                                // Set schedule type to 'scheduled'
                                                homeController.scheduleType
                                                    .value = 'scheduled';
                                                homeController
                                                    .scheduledDate.value = date;
                                                homeController.timeSlot.value =
                                                    timeSlot;

                                                print(
                                                    '🚀 Creating scheduled delivery...');
                                                print(
                                                    '📦 Item Count: $itemCount');
                                                print('⚖️ Weight: $weight lbs');
                                                print(
                                                    '📏 Package Size: $packageSize');
                                                print(
                                                    '🚛 Service: ${selectedService.name}');
                                                print(
                                                    '📅 Scheduled Date: $date');
                                                print('⏰ Time Slot: $timeSlot');

                                                // Set the selected image in home controller
                                                if (ctrl.selectedImage !=
                                                    null) {
                                                  homeController
                                                      .setItemPhotoFile(
                                                          ctrl.selectedImage);
                                                  print(
                                                      '📸 Set selected image in home controller');
                                                } else if (ctrl
                                                        .pickedFilePath !=
                                                    null) {
                                                  homeController
                                                      .setItemPhotoFile(
                                                          ctrl.pickedFilePath);
                                                  print(
                                                      '📸 Set picked file in home controller');
                                                }

                                                // Create the delivery
                                                final result =
                                                    await homeController
                                                        .createDelivery();

                                                // Navigate to appropriate screen based on result
                                                if (result) {
                                                  // Navigate to payment page after successful delivery creation
                                                  Get.to(
                                                      () =>
                                                          PaymentMethodScreen(),
                                                      transition:
                                                          Transition.cupertino);
                                                } else {
                                                  // Stay on current screen if delivery failed
                                                  // Error message already shown by createDelivery
                                                }
                                              });
                                            },
                                          ),
                                        );
                                      } else {
                                        ScaffoldMessenger.of(context)
                                            .showSnackBar(SnackBar(
                                          content: Text('Image is Required'),
                                          backgroundColor: AppColors.redColor,
                                        ));
                                      }
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
          ),
        ],
      ),
    );
  }

  Widget _previewBox() {
    return Container(
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
    );
  }

  Widget _iconButton(VoidCallback onTap, IconData icon) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 25.w,
        height: 25.w,
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(5.r),
        ),
        child: Icon(icon, size: 20.sp),
      ),
    );
  }

  Widget _imageButton(VoidCallback onTap, IconData icon) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 35.w,
        height: 35.h,
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Icon(icon, size: 15.sp, color: Colors.teal),
      ),
    );
  }

  Widget _buildCargoVanCard(CarModel model) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.r)),
      child: Container(
        width: ScreenUtil().screenWidth,
        padding: EdgeInsets.all(10.w),
        decoration: BoxDecoration(
          color: AppColors.primaryColor.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12.r),
        ),
        child: Row(
          children: [
            // Van Icon
            Image.asset(
              widget.model.imagesecond!,
              width: 100.w,
              height: 50.h,
              fit: BoxFit.contain,
            ),
            SizedBox(width: 12.w),

            // Text & Bag Info Column
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  /// Vehicle Name - Flexible with ellipsis
                  TextWidget(
                    text: widget.model.name ?? '',
                    fontSize: 15.sp,
                    fontWeight: FontWeight.w600,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  SizedBox(height: 8.h),

                  /// Bag Info Row
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: [
                      SvgPicture.asset(AppIcons.smallbagicon),
                      // SizedBox(width: 4.w),
                      Expanded(
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: TextWidget(
                            textAlign: TextAlign.start,
                            text: widget.model.smallbagcount ?? '',
                            fontSize: 10.sp,
                            fontWeight: FontWeight.w500,
                            // maxLines: 1,
                            // overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                      SizedBox(width: 12.w),
                      SvgPicture.asset(AppIcons.largebagIcon),
                      // SizedBox(width: 4.w),
                      Expanded(
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: TextWidget(
                            textAlign: TextAlign.start,
                            text: widget.model.largebagcount ?? '',
                            fontSize: 10.sp,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 10.h),

                  /// Pickup Time - Also safe from overflow
                  TextWidget(
                    text: widget.model.pickuptime ?? '',
                    fontSize: 10.sp,
                    fontWeight: FontWeight.w500,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServiceItem(String iconPath, String title,
      void Function()? onTap, int index, CarController ctrl) {
    return Padding(
      padding: EdgeInsets.only(right: 12.w),
      child: Column(
        children: [
          CustomContainer(
            onTap: onTap,
            height: 45.w,
            width: 45.w,
            color: ctrl.selectedindex.value == index
                ? AppColors.primaryColor.withOpacity(0.2)
                : AppColors.tabColor,
            borderRadius: 12.r,
            child: Center(
              child: Image.asset(
                iconPath,
                width: 30.w,
                height: 30.h,
              ),
            ),
          ),
          SizedBox(height: 4.h),
          TextWidget(
            text: title,
            fontSize: 10.sp,
            fontWeight: FontWeight.w600,
          ),
        ],
      ),
    );
  }

  Widget buildTimelineItem() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Top solid circle with pin
        Stack(
          alignment: Alignment.center,
          children: [
            CircleAvatar(radius: 15.r, backgroundColor: AppColors.tabColor),
            Icon(Icons.location_on, color: Colors.teal[800], size: 15.sp),
          ],
        ),

        buildTimelineNode(),

        // Bottom dotted circle with pin
        Stack(
          alignment: Alignment.center,
          children: [
            SizedBox(
              width: 20.w,
              height: 30.h,
              child: const DottedCircle(),
            ),
            Icon(Icons.location_on, color: Colors.teal[800], size: 15.sp),
          ],
        ),
      ],
    );
  }

  Widget buildTimelineNode() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 🔹 Solid line above the circle
        Container(
          width: 2.w,
          height: 10.h,
          color: AppColors.primaryColor,
        ),

        // 🔵 Solid circle
        Container(
          width: 10.w,
          height: 10.w,
          decoration: BoxDecoration(
            color: AppColors.primaryColor,
            shape: BoxShape.circle,
          ),
        ),

        // ⚫ Dashed rounded vertical line
        SizedBox(
          height: 15.h,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.start,
            children: List.generate(3, (index) {
              return Padding(
                padding: EdgeInsets.symmetric(vertical: .5.h),
                child: Container(
                  width: 2.w,
                  height: 4.h,
                  decoration: BoxDecoration(
                    color: Colors.black,
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                ),
              );
            }),
          ),
        ),
      ],
    );
  }

  Widget locationCard({required String from, required String to}) {
    final HomeController ctrl = Get.find<HomeController>();
    return Expanded(
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
        decoration: BoxDecoration(
          color: const Color(0xFFF8F8F8),
          borderRadius: BorderRadius.circular(12.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            GestureDetector(
                onTap: () {
                  Get.to(
                      () => SearchScreen(
                            location: ctrl.fromlocation.value,
                            tolocation: false,
                          ),
                      transition: Transition.cupertino);
                },
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextWidget(
                      text: 'From',
                      fontSize: 10.sp,
                      color: Colors.grey,
                      fontWeight: FontWeight.w600,
                    ),
                    SizedBox(height: 4.h),
                    TextWidget(
                      text: from,
                      fontSize: 12.sp,
                      fontWeight: FontWeight.w500,
                      color: Colors.black,
                    ),
                  ],
                )),
            Padding(
              padding: EdgeInsets.symmetric(vertical: 10.h),
              child: DottedLine(
                dashLength: 4.w,
                dashColor: Colors.grey.shade300,
              ),
            ),
            GestureDetector(
              onTap: () {
                Get.to(
                    () => SearchScreen(
                          location: ctrl.tolocation.value,
                          tolocation: true,
                        ),
                    transition: Transition.cupertino);
              },
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextWidget(
                    text: 'To',
                    fontSize: 10.sp,
                    color: Colors.grey,
                    fontWeight: FontWeight.w600,
                  ),
                  SizedBox(height: 4.h),
                  TextWidget(
                    text: to,
                    fontSize: 12.sp,
                    fontWeight: FontWeight.w500,
                    color: Colors.black,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 🔳 Dashed line painter
class DashedLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const dashHeight = 4.0;
    const dashSpace = 4.0;
    final paint = Paint()
      ..color = Colors.teal[800]!
      ..strokeWidth = 2.w;

    double startY = 0;
    while (startY < size.height) {
      canvas.drawLine(
          Offset(0, startY), Offset(0, startY + dashHeight.h), paint);
      startY += (dashHeight + dashSpace).h;
    }
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => false;
}

// 🔘 Dotted circle painter
class DottedCircle extends StatelessWidget {
  const DottedCircle({super.key});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: DottedCirclePainter(),
      size: Size(20.w, 20.h),
    );
  }
}

class DottedCirclePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const dotCount = 12;
    final radius = 15.r;
    final dotPaint = Paint()..color = Colors.black;

    for (int i = 0; i < dotCount; i++) {
      final angle = (2 * pi / dotCount) * i;
      final offset = Offset(
        size.width / 2 + radius * cos(angle),
        size.height / 2 + radius * sin(angle),
      );
      canvas.drawCircle(offset, 2.r, dotPaint);
    }
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => false;
}
