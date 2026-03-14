import cv2
import pyrealsense2 as rs
import numpy as np

# Initialize RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# Callback function for trackbars
def nothing(x):
    pass

# Create a window for the sliders
cv2.namedWindow("HSV Tuner")

# Create trackbars for HSV tuning
cv2.createTrackbar("H Lower", "HSV Tuner", 90, 179, nothing)
cv2.createTrackbar("H Upper", "HSV Tuner", 179, 179, nothing)
cv2.createTrackbar("Invert H", "HSV Tuner", 0, 1, nothing)  # New trackbar for inversion
cv2.createTrackbar("S Lower", "HSV Tuner", 140, 255, nothing)
cv2.createTrackbar("S Upper", "HSV Tuner", 255, 255, nothing)
cv2.createTrackbar("V Lower", "HSV Tuner", 25, 255, nothing)
cv2.createTrackbar("V Upper", "HSV Tuner", 255, 255, nothing)

try:
    while True:
        # Get frames from the RealSense camera
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        # Convert RealSense frame to OpenCV format
        color_image = np.asanyarray(color_frame.get_data())

        # Convert to HSV color space
        hsv_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)

        # Get current trackbar positions
        h_lower = cv2.getTrackbarPos("H Lower", "HSV Tuner")
        h_upper = cv2.getTrackbarPos("H Upper", "HSV Tuner")
        invert_h = cv2.getTrackbarPos("Invert H", "HSV Tuner")  # Get inversion state
        s_lower = cv2.getTrackbarPos("S Lower", "HSV Tuner")
        s_upper = cv2.getTrackbarPos("S Upper", "HSV Tuner")
        v_lower = cv2.getTrackbarPos("V Lower", "HSV Tuner")
        v_upper = cv2.getTrackbarPos("V Upper", "HSV Tuner")

        # Define HSV range based on trackbar positions
        lower_bound = np.array([h_lower, s_lower, v_lower])
        upper_bound = np.array([h_upper, s_upper, v_upper])

        if invert_h:
            # Handle inverted hue selection
            mask1 = cv2.inRange(hsv_image, np.array([0, s_lower, v_lower]), np.array([h_lower, s_upper, v_upper]))
            mask2 = cv2.inRange(hsv_image, np.array([h_upper, s_lower, v_lower]), np.array([179, s_upper, v_upper]))
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            # Regular hue selection
            mask = cv2.inRange(hsv_image, lower_bound, upper_bound)

        # Show the original and masked images
        cv2.imshow("Original", color_image)
        cv2.imshow("Mask", mask)

        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Release resources
    pipeline.stop()
    cv2.destroyAllWindows()
