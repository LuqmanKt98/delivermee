import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ConfirmDeliveryController extends GetxController
    with GetSingleTickerProviderStateMixin {
  var currentStep = 0.obs;
   late AnimationController animationController;
  late Animation<double> progressAnimation;

  void initializeStep(int step) {
    currentStep.value = step;
    animateToStep(step);
  }

  @override
  void onInit() {
    animationController = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 600),
    );
    progressAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(animationController);
    super.onInit();
  }

  void nextStep() {
    if (currentStep.value < 3) {
      currentStep.value++;
      animateToStep(currentStep.value);
    }
  }

  void animateToStep(int step) {
    final target = step / 3; // 3 gaps between 4 points
    animationController.animateTo(target);
  }

  @override
  void onClose() {
    animationController.dispose();
    super.onClose();
  }
}
