import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/custom_container.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/common/widgets/live_map_widget.dart';
import 'package:deliver_mee/src/feature/user/car_selection/car_selection.dart';
import 'package:deliver_mee/src/feature/user/car_selection/controller.dart';
import 'package:deliver_mee/src/feature/user/home/controller/controller.dart';
import 'package:deliver_mee/src/feature/user/notification/notification.dart';
import 'package:deliver_mee/src/feature/user/search/search.dart';
import 'package:deliver_mee/src/feature/user/delivery_details/delivery_details_form.dart';
import 'package:dotted_line/dotted_line.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class UserHomeScreen extends StatelessWidget {
  UserHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final HomeController ctrl = Get.find<HomeController>();
    return Scaffold(
      body: Stack(
        children: [
          // Live Map Section
          Container(
            height: 450.h,
            width: double.infinity,
            child: Stack(
              children: [
                // Live Map Widget
                LiveMapWidget(
                  height: 450.h,
                  showSearchButton: false,
                  onLocationSelected: (LatLng location) {
                    // Handle location selection
                    print(
                        'Selected location: ${location.latitude}, ${location.longitude}');
                  },
                ),
              ],
            ),
          ),

          // Bottom Sheet
          Align(
            alignment: Alignment.bottomCenter,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Padding(
                  padding: EdgeInsets.all(16.w),
                  child: FloatingActionButton(
                    backgroundColor: AppColors.whiteColor,
                    shape: CircleBorder(),
                    onPressed: () {},
                    child: SvgPicture.asset(
                      AppIcons.currentlocationIcon,
                      width: 30.w,
                      height: 30.h,
                    ),
                  ),
                ),
                SizedBox(
                  height: 20.h,
                ),
                Container(
                  padding:
                      EdgeInsets.symmetric(horizontal: 16.w, vertical: 20.h),
                  width: double.infinity,
                  constraints: BoxConstraints(
                    maxHeight: MediaQuery.of(context).size.height * 0.6,
                    minHeight: 400.h,
                  ),
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
                        TextWidget(
                          text: 'Start the Delivery',
                          fontSize: 20.sp,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 8.h),
                        TextWidget(
                          text:
                              'Select pickup and dropoff locations to continue',
                          fontSize: 12.sp,
                          color: Colors.grey[600],
                          fontWeight: FontWeight.w400,
                        ),
                        SizedBox(height: 16.h),
                        locationCard(ctrl: ctrl),
                        SizedBox(height: 20.h),
                        TextWidget(
                          text: 'Choose a service',
                          fontSize: 16.sp,
                          fontWeight: FontWeight.w600,
                        ),
                        SizedBox(height: 10.h),
                        SizedBox(
                          height: 120.h,
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: List.generate(
                                ctrl.carslist.length,
                                (index) => _buildServiceItem(
                                    ctrl.carslist[index].image!,
                                    ctrl.carslist[index].name!, () {
                                  Get.find<CarController>()
                                      .selectedindex
                                      .value = index;

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

                                  Get.to(
                                      () => CarSelectionScreen(
                                            model: ctrl.carslist[index],
                                          ),
                                      transition: Transition.cupertino);
                                }),
                              ),
                            ),
                          ),
                        ),
                        SizedBox(height: 20.h),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget locationCard({required HomeController ctrl}) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F8F8),
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(
          color: (ctrl.fromlocation.value.isNotEmpty &&
                  ctrl.tolocation.value.isNotEmpty)
              ? AppColors.primaryColor.withOpacity(0.3)
              : Colors.grey.shade300,
          width: 1.5,
        ),
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
              child: Obx(() => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.location_on,
                            color: ctrl.fromlocation.value.isNotEmpty
                                ? AppColors.primaryColor
                                : Colors.grey,
                            size: 14.sp,
                          ),
                          SizedBox(width: 4.w),
                          TextWidget(
                            text: 'From',
                            fontSize: 10.sp,
                            color: ctrl.fromlocation.value.isNotEmpty
                                ? AppColors.primaryColor
                                : Colors.grey,
                            fontWeight: FontWeight.w600,
                          ),
                          if (ctrl.fromlocation.value.isNotEmpty)
                            Padding(
                              padding: EdgeInsets.only(left: 4.w),
                              child: Icon(
                                Icons.check_circle,
                                color: AppColors.primaryColor,
                                size: 12.sp,
                              ),
                            ),
                        ],
                      ),
                      SizedBox(height: 4.h),
                      TextWidget(
                        text: ctrl.fromlocation.value.isNotEmpty
                            ? ctrl.fromlocation.value
                            : 'Tap to select pickup location',
                        fontSize: 12.sp,
                        fontWeight: FontWeight.w500,
                        color: ctrl.fromlocation.value.isNotEmpty
                            ? Colors.black
                            : Colors.grey,
                      ),
                    ],
                  ))),
          Padding(
            padding: EdgeInsets.symmetric(vertical: 10.h),
            child: DottedLine(
              dashLength: 4.w,
              dashColor: (ctrl.fromlocation.value.isNotEmpty &&
                      ctrl.tolocation.value.isNotEmpty)
                  ? AppColors.primaryColor.withOpacity(0.3)
                  : Colors.grey.shade300,
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
            child: Obx(() => Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.location_on,
                          color: ctrl.tolocation.value.isNotEmpty
                              ? AppColors.primaryColor
                              : Colors.grey,
                          size: 14.sp,
                        ),
                        SizedBox(width: 4.w),
                        TextWidget(
                          text: 'To',
                          fontSize: 10.sp,
                          color: ctrl.tolocation.value.isNotEmpty
                              ? AppColors.primaryColor
                              : Colors.grey,
                          fontWeight: FontWeight.w600,
                        ),
                        if (ctrl.tolocation.value.isNotEmpty)
                          Padding(
                            padding: EdgeInsets.only(left: 4.w),
                            child: Icon(
                              Icons.check_circle,
                              color: AppColors.primaryColor,
                              size: 12.sp,
                            ),
                          ),
                      ],
                    ),
                    SizedBox(height: 4.h),
                    TextWidget(
                      text: ctrl.tolocation.value.isNotEmpty
                          ? ctrl.tolocation.value
                          : 'Tap to select dropoff location',
                      fontSize: 12.sp,
                      fontWeight: FontWeight.w500,
                      color: ctrl.tolocation.value.isNotEmpty
                          ? Colors.black
                          : Colors.grey,
                    ),
                  ],
                )),
          ),
        ],
      ),
    );
  }

  Widget _buildServiceItem(
      String iconPath, String title, void Function()? onTap) {
    return Padding(
      padding: EdgeInsets.only(right: 12.w),
      child: Column(
        children: [
          CustomContainer(
            onTap: onTap,
            height: 45.w,
            width: 45.w,
            color: AppColors.tabColor,
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

  Widget notificationBell({int notificationCount = 4}) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        GestureDetector(
          onTap: () {
            Get.to(() => NotificationScreen(),
                transition: Transition.cupertino);
          },
          child: Container(
            width: 45.w,
            height: 45.h,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white,
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: Center(
              child: SvgPicture.asset(
                AppIcons.bellIcon,
                height: 30.h,
              ),
            ),
          ),
        ),
        if (notificationCount > 0)
          Positioned(
            top: -2.h,
            right: -2.w,
            child: Container(
              padding: EdgeInsets.all(4.w),
              decoration: BoxDecoration(
                color: const Color(0xFF006B6A),
                shape: BoxShape.circle,
              ),
              constraints: BoxConstraints(
                minWidth: 15.w,
                minHeight: 15.h,
              ),
              child: Center(
                child: TextWidget(
                  text: '$notificationCount',
                  color: Colors.white,
                  fontSize: 10.sp,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }

  /// Show delivery details dialog
  void _showDeliveryDetailsDialog(HomeController ctrl) {
    // Validate that both locations are selected
    if (ctrl.fromlocation.value.isEmpty || ctrl.tolocation.value.isEmpty) {
      String missingLocation = '';
      if (ctrl.fromlocation.value.isEmpty && ctrl.tolocation.value.isEmpty) {
        missingLocation = 'both pickup and dropoff locations';
      } else if (ctrl.fromlocation.value.isEmpty) {
        missingLocation = 'pickup location';
      } else {
        missingLocation = 'dropoff location';
      }

      Get.snackbar(
        'Location Required',
        'Please select $missingLocation to continue',
        backgroundColor: Colors.orange,
        colorText: Colors.white,
        duration: Duration(seconds: 4),
        icon: Icon(Icons.location_on, color: Colors.white),
        snackPosition: SnackPosition.TOP,
      );
      return;
    }

    // Navigate to delivery details form
    Get.to(
      () => const DeliveryDetailsForm(),
      transition: Transition.cupertino,
    );
  }
}
