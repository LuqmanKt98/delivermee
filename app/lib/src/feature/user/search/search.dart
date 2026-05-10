import 'dart:async';
import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/user/home/controller/controller.dart';
import 'package:deliver_mee/src/common/services/location_service.dart';
import 'package:deliver_mee/src/common/services/location_suggestion_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:get/get.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geocoding/geocoding.dart';

class SearchScreen extends StatefulWidget {
  final bool tolocation;
  final String location;
  SearchScreen({
    super.key,
    required this.tolocation,
    required this.location,
  });

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  late GoogleMapController _mapController;
  final LocationService _locationService = LocationService.to;
  final LocationSuggestionService _suggestionService =
      LocationSuggestionService.to;
  final TextEditingController _searchController = TextEditingController();

  // Map state
  LatLng _selectedLocation = const LatLng(40.7128, -74.0060); // Default to NYC
  Set<Marker> _markers = {};
  String _selectedAddress = '';
  bool _showSuggestions = false;

  // Camera position
  CameraPosition get _cameraPosition => CameraPosition(
        target: _selectedLocation,
        zoom: 15.0,
      );

  @override
  void initState() {
    super.initState();
    _selectedAddress = widget.location;
    _searchController.text = widget.location; // Pre-fill search field
    _initializeLocation();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Initialize location and map
  Future<void> _initializeLocation() async {
    try {
      // Get current location
      final location = await _locationService.getCurrentLocation();
      if (location != null &&
          location.latitude != null &&
          location.longitude != null) {
        _selectedLocation = LatLng(location.latitude!, location.longitude!);
        _getAddressFromPosition(_selectedLocation);
      }

      // Add marker for selected location
      _markers.add(
        Marker(
          markerId: const MarkerId('selected_location'),
          position: _selectedLocation,
          infoWindow: InfoWindow(
            title: widget.tolocation ? 'To Location' : 'From Location',
            snippet: _selectedAddress,
          ),
          icon: BitmapDescriptor.defaultMarkerWithHue(
            widget.tolocation
                ? BitmapDescriptor.hueRed
                : BitmapDescriptor.hueBlue,
          ),
        ),
      );

      if (mounted) {
        setState(() {});
      }
    } catch (e) {
      print('❌ Error initializing location: $e');
    }
  }

  /// Get address from position
  Future<void> _getAddressFromPosition(LatLng position) async {
    try {
      final placemarks = await placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );

      if (placemarks.isNotEmpty) {
        final placemark = placemarks.first;
        final address =
            '${placemark.street}, ${placemark.locality}, ${placemark.administrativeArea}';
        setState(() {
          _selectedAddress = address;
        });
      }
    } catch (e) {
      print('❌ Error getting address: $e');
      setState(() {
        _selectedAddress =
            'Location: ${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}';
      });
    }
  }

  /// Search for location suggestions
  void _searchLocation(String query) {
    if (query.isEmpty) {
      setState(() {
        _showSuggestions = false;
      });
      _suggestionService.clearSuggestions();
      return;
    }

    setState(() {
      _showSuggestions = true;
    });

    _suggestionService.searchSuggestions(query);
  }

  /// Select a location from suggestions
  void _selectSuggestion(LocationSuggestion suggestion) {
    setState(() {
      _selectedLocation = LatLng(suggestion.latitude, suggestion.longitude);
      _selectedAddress = suggestion.address;
      _showSuggestions = false;
      _searchController.text = suggestion.address;

      _markers.clear();
      _markers.add(
        Marker(
          markerId: const MarkerId('selected_location'),
          position: _selectedLocation,
          infoWindow: InfoWindow(
            title: widget.tolocation ? 'To Location' : 'From Location',
            snippet: suggestion.address,
          ),
          icon: BitmapDescriptor.defaultMarkerWithHue(
            widget.tolocation
                ? BitmapDescriptor.hueRed
                : BitmapDescriptor.hueBlue,
          ),
        ),
      );
    });

    // Move camera to new location
    _mapController.animateCamera(
      CameraUpdate.newLatLng(_selectedLocation),
    );

    // Clear suggestions
    _suggestionService.clearSuggestions();
  }

  /// Handle map tap
  void _onMapTap(LatLng position) {
    setState(() {
      _selectedLocation = position;
      _markers.clear();
      _markers.add(
        Marker(
          markerId: const MarkerId('selected_location'),
          position: _selectedLocation,
          infoWindow: InfoWindow(
            title: widget.tolocation ? 'To Location' : 'From Location',
            snippet: _selectedAddress,
          ),
          icon: BitmapDescriptor.defaultMarkerWithHue(
            widget.tolocation
                ? BitmapDescriptor.hueRed
                : BitmapDescriptor.hueBlue,
          ),
        ),
      );
    });

    _getAddressFromPosition(position);
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<HomeController>();

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: Stack(
        children: [
          // Google Maps
          Positioned.fill(
            child: GoogleMap(
              initialCameraPosition: _cameraPosition,
              onMapCreated: (GoogleMapController controller) {
                _mapController = controller;
              },
              onTap: _onMapTap,
              markers: _markers,
              myLocationEnabled: true,
              myLocationButtonEnabled: false,
              zoomControlsEnabled: false,
            ),
          ),

          // Location top bar
          Positioned(
            top: 30.h,
            left: 20.w,
            right: 20.w,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                GestureDetector(
                  onTap: () {
                    FocusScope.of(context).unfocus();
                    Get.back();
                  },
                  child: Container(
                    width: 45.w,
                    height: 45.h,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white,
                      border: Border.all(color: Colors.grey.shade300),
                    ),
                    child: const Center(child: Icon(Icons.arrow_back)),
                  ),
                ),
                SizedBox(height: 20.h),
                Container(
                  padding:
                      EdgeInsets.symmetric(horizontal: 15.w, vertical: 10.h),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12.r),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black12,
                        blurRadius: 6,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      SvgPicture.asset(
                        AppIcons.pinIcon,
                        height: 22.h,
                        width: 22.w,
                        color: _selectedAddress.isNotEmpty
                            ? AppColors.primaryColor
                            : Colors.grey,
                      ),
                      SizedBox(width: 5.w),
                      Expanded(
                        child: TextWidget(
                          text: _selectedAddress.isNotEmpty
                              ? _selectedAddress
                              : widget.location,
                          fontSize: 14.sp,
                          fontWeight: FontWeight.w400,
                          color: _selectedAddress.isNotEmpty
                              ? Colors.black
                              : Colors.grey,
                        ),
                      ),
                      if (_selectedAddress.isNotEmpty)
                        Icon(
                          Icons.check_circle,
                          color: AppColors.primaryColor,
                          size: 20.sp,
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // My Location button
          Positioned(
            right: 20.w,
            top: 300.h,
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12.r),
                boxShadow: [
                  BoxShadow(color: Colors.black12, blurRadius: 4),
                ],
              ),
              child: IconButton(
                onPressed: () async {
                  final location = await _locationService.getCurrentLocation();
                  if (location != null &&
                      location.latitude != null &&
                      location.longitude != null) {
                    final newPosition =
                        LatLng(location.latitude!, location.longitude!);
                    _onMapTap(newPosition);
                    _mapController.animateCamera(
                      CameraUpdate.newLatLng(newPosition),
                    );
                  }
                },
                icon: SvgPicture.asset(
                  AppIcons.currentlocationIcon,
                  width: 20.w,
                  height: 20.h,
                ),
              ),
            ),
          ),

          // Search Location bottom bar
          Positioned(
            left: 20.w,
            right: 20.w,
            bottom: 40.h,
            child: Padding(
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(context).viewInsets.bottom),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding:
                        EdgeInsets.symmetric(horizontal: 15.w, vertical: 12.h),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12.r),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black12,
                          blurRadius: 6,
                          offset: Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.search,
                          size: 20.sp,
                          color: AppColors.primaryColor,
                        ),
                        SizedBox(width: 10.w),

                        // Flexible TextField to avoid overflow
                        Expanded(
                          child: TextField(
                            controller: _searchController,
                            onChanged: (value) {
                              _searchLocation(value);
                            },
                            onSubmitted: (value) {
                              _searchLocation(value);
                            },
                            style: TextStyle(
                              fontSize: 14.sp,
                              fontWeight: FontWeight.w500,
                            ),
                            decoration: InputDecoration(
                              isCollapsed: true, // removes extra vertical space
                              contentPadding: EdgeInsets.zero,
                              hintText: widget.tolocation
                                  ? 'Search dropoff location...'
                                  : 'Search pickup location...',
                              hintStyle: TextStyle(
                                fontSize: 14.sp,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey,
                              ),
                              border: InputBorder.none,
                              suffixIcon: Obx(() {
                                if (_suggestionService.isSearching) {
                                  return SizedBox(
                                    width: 20.w,
                                    height: 20.h,
                                    child: Padding(
                                      padding: EdgeInsets.all(8.w),
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor:
                                            AlwaysStoppedAnimation<Color>(
                                          AppColors.primaryColor,
                                        ),
                                      ),
                                    ),
                                  );
                                } else if (_selectedAddress.isNotEmpty) {
                                  return Icon(
                                    Icons.check_circle,
                                    color: AppColors.primaryColor,
                                    size: 20.sp,
                                  );
                                }
                                return SizedBox.shrink();
                              }),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Location Suggestions
                  if (_showSuggestions)
                    Obx(() => _suggestionService.suggestions.isNotEmpty
                        ? Container(
                            margin: EdgeInsets.only(top: 10.h),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12.r),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black12,
                                  blurRadius: 6,
                                  offset: Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Column(
                              children: _suggestionService.suggestions
                                  .map((suggestion) =>
                                      _buildSuggestionItem(suggestion))
                                  .toList(),
                            ),
                          )
                        : SizedBox.shrink()),

                  SizedBox(height: 20.h),
                  // Confirm Location Button
                  Container(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        if (_selectedAddress.isNotEmpty &&
                            _selectedAddress != '' &&
                            _selectedAddress !=
                                'Location: ${_selectedLocation.latitude.toStringAsFixed(4)}, ${_selectedLocation.longitude.toStringAsFixed(4)}') {
                          if (widget.tolocation) {
                            ctrl.updateToLocation(
                                _selectedAddress,
                                _selectedLocation.latitude,
                                _selectedLocation.longitude);
                          } else {
                            ctrl.updateFromLocation(
                                _selectedAddress,
                                _selectedLocation.latitude,
                                _selectedLocation.longitude);
                          }

                          // Show success feedback
                          Get.snackbar(
                            'Location Selected',
                            widget.tolocation
                                ? 'Dropoff location set successfully!'
                                : 'Pickup location set successfully!',
                            backgroundColor: Colors.green,
                            colorText: Colors.white,
                            duration: Duration(seconds: 2),
                            icon: Icon(Icons.check_circle, color: Colors.white),
                          );

                          Get.back();
                        } else {
                          Get.snackbar(
                            'Location Required',
                            'Please search and select a valid location before confirming',
                            backgroundColor: Colors.orange,
                            colorText: Colors.white,
                            duration: Duration(seconds: 3),
                            icon: Icon(Icons.location_on, color: Colors.white),
                          );
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _selectedAddress.isNotEmpty &&
                                _selectedAddress != '' &&
                                _selectedAddress !=
                                    'Location: ${_selectedLocation.latitude.toStringAsFixed(4)}, ${_selectedLocation.longitude.toStringAsFixed(4)}'
                            ? AppColors.primaryColor
                            : Colors.grey,
                        padding: EdgeInsets.symmetric(vertical: 15.h),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12.r),
                        ),
                      ),
                      child: Obx(() => _suggestionService.isSearching
                          ? Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                SizedBox(
                                  width: 20.w,
                                  height: 20.h,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    valueColor: AlwaysStoppedAnimation<Color>(
                                      Colors.white,
                                    ),
                                  ),
                                ),
                                SizedBox(width: 10.w),
                                TextWidget(
                                  text: 'Searching...',
                                  color: Colors.white,
                                  fontSize: 16.sp,
                                  fontWeight: FontWeight.w600,
                                ),
                              ],
                            )
                          : TextWidget(
                              text: 'Confirm Location',
                              color: Colors.white,
                              fontSize: 16.sp,
                              fontWeight: FontWeight.w600,
                            )),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build suggestion item widget
  Widget _buildSuggestionItem(LocationSuggestion suggestion) {
    return InkWell(
      onTap: () => _selectSuggestion(suggestion),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: Colors.grey.shade200,
              width: 0.5,
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.location_on,
              color: AppColors.primaryColor,
              size: 20.sp,
            ),
            SizedBox(width: 12.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextWidget(
                    text: suggestion.address,
                    fontSize: 14.sp,
                    fontWeight: FontWeight.w500,
                    color: Colors.black87,
                  ),
                  if (suggestion.description?.isNotEmpty == true) ...[
                    SizedBox(height: 2.h),
                    TextWidget(
                      text: suggestion.description!,
                      fontSize: 12.sp,
                      fontWeight: FontWeight.w400,
                      color: Colors.grey.shade600,
                    ),
                  ],
                ],
              ),
            ),
            Icon(
              Icons.arrow_forward_ios,
              color: Colors.grey.shade400,
              size: 16.sp,
            ),
          ],
        ),
      ),
    );
  }
}
