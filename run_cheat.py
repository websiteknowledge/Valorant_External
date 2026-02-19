import sys
import numpy as np
import cv2
import mss
import time
import clr
import ctypes
import keyboard

# 1. FORCE PIXEL ACCURACY
ctypes.windll.shcore.SetProcessDpiAwareness(1)
USER32 = ctypes.windll.user32

# 2. DRIVER
DLL_PATH = r"C:\ValorantAI\Logitech CVE.dll"
try:
    clr.AddReference(DLL_PATH)
    from CVE import Mouse 
    Mouse.Initialize("LGHUB")
    Mouse.Open()
    print("[+] Nearest-Target Lock ACTIVE.")
except:
    sys.exit("[-] DLL Error: Check your Logitech DLL path.")

# 3. SETTINGS
SCAN_SIZE = 100         # FOV
SMOOTH = 0.1           # Speed
RECOIL_PULL = 8        # Pulldown
offset_x = 7
offset_y = 1.5

# PURPLE RANGE
PURPLE_LOWER = np.array([140, 110, 90]) 
PURPLE_UPPER = np.array([160, 255, 255])

def run():
    global offset_x, offset_y
    with mss.mss() as sct:
        sw = USER32.GetSystemMetrics(0)
        sh = USER32.GetSystemMetrics(1)
        
        # Pre-calculate center of the SCAN_SIZE box
        mid_p = SCAN_SIZE // 2

        while True:
            # LIVE CALIBRATION
            if keyboard.is_pressed('up'): offset_y -= 1; print(f"Y: {offset_y}")
            if keyboard.is_pressed('down'): offset_y += 1; print(f"Y: {offset_y}")
            if keyboard.is_pressed('left'): offset_x -= 1; print(f"X: {offset_x}")
            if keyboard.is_pressed('right'): offset_x += 1; print(f"X: {offset_x}")

            zone = {
                "top": int((sh // 2) - mid_p + offset_y),
                "left": int((sw // 2) - mid_p + offset_x),
                "width": SCAN_SIZE,
                "height": SCAN_SIZE
            }

            img = np.array(sct.grab(zone))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, PURPLE_LOWER, PURPLE_UPPER)
            
            # --- THE FIX: FIND ALL PURPLE OBJECTS ---
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_target = None
            min_dist = float('inf')

            for cnt in contours:
                if cv2.contourArea(cnt) < 5: continue # Ignore tiny pixels
                
                # Get center of THIS specific purple object
                M = cv2.moments(cnt)
                if M["m00"] == 0: continue
                
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                
                # Calculate distance from your crosshair (mid_p, mid_p)
                dist = np.sqrt((cX - mid_p)**2 + (cY - mid_p)**2)
                
                # If this purple is closer to crosshair than the previous one, pick it
                if dist < min_dist:
                    min_dist = dist
                    best_target = (cX, cY)

            # --- EXECUTE LOCK ON NEAREST ---
            if best_target:
                tx, ty = best_target
                
                # Aim at the TOP of that specific target (Head bias)
                # We subtract a few pixels from ty to go higher
                ty -= 5 

                rel_x = tx - mid_p
                rel_y = ty - mid_p

                # Snap to the closest enemy only
                if abs(rel_x) > 1 or abs(rel_y) > 1:
                    Mouse.Move(0, int(rel_x * SMOOTH), int(rel_y * SMOOTH), 0)

                # Trigger Logic
                if min_dist < 6: # Only fire if the closest target is very near center
                    Mouse.Move(1, 0, 0, 0)
                    time.sleep(0.01)
                    Mouse.Move(0, 0, 0, 0)
                    Mouse.Move(0, 0, RECOIL_PULL, 0)
                    time.sleep(0.1)

            if keyboard.is_pressed('q'): break
            time.sleep(0.001)

if __name__ == "__main__":
    run()