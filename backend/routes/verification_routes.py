# verification_routes.py — superseded by Firebase Auth
#
# All OTP, email verification, phone verification, and password reset flows are
# now handled client-side via the Firebase Auth SDK:
#
#   Email verification  → FirebaseAuth.currentUser.sendEmailVerification()
#   Phone OTP           → FirebaseAuth.verifyPhoneNumber()
#   Forgot password     → FirebaseAuth.sendPasswordResetEmail()
#
# This file is intentionally empty. The namespace is not registered in app.py.
