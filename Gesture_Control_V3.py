import cv2
import pyautogui
from HandTrackingModule import HandTrackingModule
import screen_brightness_control as sbc
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import time, math, numpy as np

# Initialize audio for volume control
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()
minVol, maxVol = volRange[0], volRange[1]

# Initialize the hand detector
detector = HandTrackingModule(detectionCon=0.8, trackCon=0.8)

# Screen size for cursor control
screenWidth, screenHeight = pyautogui.size()

# Smoothing variables for cursor movement
prevCursorX, prevCursorY = 0, 0
smoothFactor = 5

# Gesture stability and debounce
gesture_stable_frames = 0
last_detected_gesture = None
last_command_time = time.time()
command_cooldown = 1  # Minimum time (in seconds) between commands

# Optional: Disable PyAutoGUI fail-safe for testing (use cautiously)
pyautogui.FAILSAFE = False  # Set to True in production for safety

cap = cv2.VideoCapture(0)
while True:
    success, img = cap.read()
    if not success:
        break

    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)

    if len(lmList) != 0:
        # Right hand gestures
        thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip = 4, 8, 12, 16, 20

        # Cursor control (index finger)
        cursorX = int((lmList[index_tip][1] / img.shape[1]) * screenWidth)
        cursorY = int((lmList[index_tip][2] / img.shape[0]) * screenHeight)
        cursorX = prevCursorX + (cursorX - prevCursorX) / smoothFactor
        cursorY = prevCursorY + (cursorY - prevCursorY) / smoothFactor
        pyautogui.moveTo(cursorX, cursorY)
        prevCursorX, prevCursorY = cursorX, cursorY

        # Click control (pinch gesture)
        distance_thumb_index = detector.calculateDistance(thumb_tip, index_tip, lmList)
        distance_thumb_middle = detector.calculateDistance(thumb_tip, middle_tip, lmList)
        if distance_thumb_index < 30 and distance_thumb_middle < 30:  # Increased threshold
            pyautogui.click()

        # Scroll control (index and middle finger)
        index_y = lmList[index_tip][2]
        middle_y = lmList[middle_tip][2]
        if abs(index_y - middle_y) > 50:
            if index_y < middle_y:
                pyautogui.scroll(300)  # Scroll up
            else:
                pyautogui.scroll(-300)  # Scroll down

        # Minimize window (all fingers open -> tips together)
        if all(lmList[finger][2] < lmList[finger - 2][2] for finger in [8, 12, 16, 20]):
            if detector.calculateDistance(thumb_tip, index_tip, lmList) < 50:  # Increased threshold
                pyautogui.hotkey('alt', 'space')
                pyautogui.press('n')

        # Close window (all fingers open -> fist)
        if all(lmList[finger][2] < lmList[0][2] for finger in [8, 12, 16, 20]):
            if detector.calculateDistance(thumb_tip, index_tip, lmList) < 30:  # Increased threshold
                pyautogui.hotkey('alt', 'f4')

        # Restore down (three fingers straight, thumb + index pinch)
        if all(lmList[finger][2] < lmList[finger - 2][2] for finger in [12, 16, 20]):
            if distance_thumb_index < 35:  # Increased threshold
                pyautogui.hotkey('win', 'down')

        # Restore up (three fingers straight, thumb + index spread)
        if all(lmList[finger][2] < lmList[finger - 2][2] for finger in [12, 16, 20]):
            if distance_thumb_index > 60:  # Increased threshold
                pyautogui.hotkey('win', 'up')

        # Left hand gestures
        # Volume control (thumb + index finger)
        if detector.calculateDistance(thumb_tip, index_tip, lmList) < 250:  # Increased threshold
            vol = math.hypot(lmList[thumb_tip][1] - lmList[index_tip][1],
                             lmList[thumb_tip][2] - lmList[index_tip][2])
            vol = max(minVol, min(maxVol, vol))  # Clamp the value
            volume.SetMasterVolumeLevel(vol, None)

        # Brightness control (thumb + middle finger)
        if detector.calculateDistance(thumb_tip, middle_tip, lmList) < 250:  # Increased threshold
            brightness = math.hypot(lmList[thumb_tip][1] - lmList[middle_tip][1],
                                    lmList[thumb_tip][2] - lmList[middle_tip][2])
            
            bright = np.interp(brightness, [5, 100], [0, 100])
            sbc.set_brightness(int(bright))
            # brightness *= 5 # Increase the sensitivity
            # brightness = max(0, min(100, int(brightness)))  # Clamp the brightness
            # sbc.set_brightness(brightness)

    # Debug output to track gesture stability
    cv2.imshow("Gesture Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
