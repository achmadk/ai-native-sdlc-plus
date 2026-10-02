# Incident 042 (fixture, 2026-09-18)

Payments retry batch scheduled during the Q3 freeze window caused double-charge alerts. Cause: worker did not check the freeze calendar. Lesson: check the freeze calendar before scheduling any payment-adjacent work.
