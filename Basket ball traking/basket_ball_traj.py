import sys
import os
import time
import numpy as np
import cv2
import math
try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    print("pyrealsense2 not available - will try regular camera")

import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import json

class BasketballTrackingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Trajectory Tracking - Optimized")
        self.root.geometry("1280x900")
        self.root.minsize(1280, 900)
        
        # Camera variables
        self.pipeline = None
        self.cap = None
        self.camera_type = "Demo"
        self.is_capturing = False
        self.trajectory = []
        self.frame_thread = None
        self.stop_threads = False
        
        # Ball detection variables
        self.posListX, self.posListY = [], []
        self.ball_detected = False
        
        # HSV values for basketball detection (orange ball)
        self.hsvVals = {'hmin': 26, 'smin': 101, 'vmin': 90, 'hmax': 94, 'smax': 184, 'vmax': 165}
        
        
        
        # Setup GUI
        self.setup_gui()
        
        # Initialize data file (CSV format)
        self.data_file = "basketball_traj_data.csv"
        self.check_create_file()
        
        # Initialize camera
        self.initialize_camera()
        
        # Bind spacebar for toggle capture
        self.root.bind('<KeyPress-space>', self.spacebar_toggle_capture)
        self.root.focus_set()  # Make sure the window can receive key events
        
    def spacebar_toggle_capture(self, event):
        """Toggle capture when spacebar is pressed - only start/stop, not reset"""
        if not self.is_capturing:
            # Start capturing
            self.start_capture()
        else:
            # Stop capturing
            self.stop_capture()
        
    def start_capture(self, reset_trajectory=True):
        """Start trajectory capture"""
        self.is_capturing = True
        if reset_trajectory:
            self.reset_trajectory()
        self.capture_button.config(text="Stop Capture (Space)")
        self.status_label.config(text="Status: Capturing...")
        self.save_button.config(state=tk.DISABLED)
        print("Capture started")

    def stop_capture(self):
        """Stop trajectory capture"""
        self.is_capturing = False
        self.capture_button.config(text="Start Capture (Space)")
        self.status_label.config(text="Status: Capture Complete")
        if len(self.posListX) > 0:
            self.save_button.config(state=tk.NORMAL)
            self.display_trajectory()
        print(f"Capture stopped - {len(self.posListX)} points captured")
        
    def setup_gui(self):
        # Create main frames
        self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Camera view and controls
        self.left_panel = ttk.Frame(self.main_frame, width=800)
        self.main_frame.add(self.left_panel, weight=3)
        
        # Camera view
        self.camera_label = ttk.Label(self.left_panel, text="Initializing camera...", 
                                     font=("Arial", 16), background="gray")
        self.camera_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Camera control buttons
        self.camera_control_frame = ttk.Frame(self.left_panel)
        self.camera_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.capture_button = ttk.Button(self.camera_control_frame, text="Start Capture (Space)", 
                                         command=self.toggle_capture_button)
        self.capture_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_trajectory_button = ttk.Button(self.camera_control_frame, text="Reset Trajectory", 
                                                 command=self.reset_trajectory)
        self.reset_trajectory_button.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(self.camera_control_frame, text="Status: Initializing...")
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Right panel - Parameters and inputs
        self.right_panel = ttk.Frame(self.main_frame, width=400)
        self.main_frame.add(self.right_panel, weight=1)
        
        # Parameters section
        self.param_frame = ttk.LabelFrame(self.right_panel, text="Technical Parameters")
        self.param_frame.pack(fill=tk.X, padx=5, pady=5, ipady=5)
        
        # Create parameter entry fields - Removed Shot Result, Added Distance
        self.params = {}
        param_entries = [
            ("Position P", "position_p", "15"),
            ("Velocity P", "velocity_p", "60"),
            ("Frequency (Hz)", "frequency", "1000"),
            ("Velocity Cutoff (Hz)", "velocity_cutoff", "500"),
            ("Battery", "battery", "602"),
            ("Battery Voltage", "voltage", "24.5"),
            ("Temperature", "temperature", "Medium"),
            ("Start Angle", "start_angle", "30"),
            ("Shoot Angle", "shoot_angle", "45"),
            ("Velocity", "velocity", "75.0"),
            ("Acceleration", "acceleration", "1650"),
            ("Distance (m)", "distance", "3.0")  # New parameter for distance
        ]
        
        param_grid_frame = ttk.Frame(self.param_frame)
        param_grid_frame.pack(fill=tk.X, padx=5, pady=5)
        
        for i, (label_text, param_name, default_val) in enumerate(param_entries):
            row = i // 2
            col = (i % 2) * 3
            
            ttk.Label(param_grid_frame, text=f"{label_text}:").grid(row=row, column=col, 
                                                                   padx=5, pady=2, sticky='e')
            param_entry = ttk.Entry(param_grid_frame, width=10)
            param_entry.insert(0, default_val)
            param_entry.grid(row=row, column=col+1, padx=5, pady=2, sticky='w')
            self.params[param_name] = param_entry
        
        
        
      
        
        # Ball Detection Status
        self.detection_frame = ttk.LabelFrame(self.right_panel, text="Ball Detection Status")
        self.detection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.detection_label = ttk.Label(self.detection_frame, text="No ball detected", 
                                         font=("Arial", 12, "bold"))
        self.detection_label.pack(padx=10, pady=10)
        
        # Save data button
        self.save_frame = ttk.Frame(self.right_panel)
        self.save_frame.pack(fill=tk.X, padx=5, pady=15)
        
        self.save_button = ttk.Button(self.save_frame, text="Save Data", 
                                      command=self.save_data, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = ttk.Button(self.save_frame, text="Reset Form", 
                                       command=self.reset_form)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        # Trajectory display
        self.trajectory_frame = ttk.LabelFrame(self.right_panel, text="Trajectory Data")
        self.trajectory_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.trajectory_text = tk.Text(self.trajectory_frame, height=8, width=40)
        self.trajectory_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar at bottom
        self.status_bar = ttk.Label(self.root, text="Initializing...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_capture_button(self):
        """Handle capture button click"""
        if not self.is_capturing:
            self.start_capture()
        else:
            self.stop_capture()

    def initialize_camera(self):
        """Initialize camera - try RealSense first, then regular camera, then demo mode"""
        print("Initializing camera...")
        
        # Try RealSense first
        if REALSENSE_AVAILABLE:
            if self.try_realsense():
                return
        
        # Try regular camera
        if self.try_regular_camera():
            return
        
        # Fall back to demo mode
        self.start_demo_mode()
        
    def try_realsense(self):
        """Try to initialize RealSense camera"""
        try:
            print("Trying RealSense camera...")
            context = rs.context()
            devices = context.query_devices()
            if len(devices) == 0:
                print("No RealSense devices found")
                return False
            
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            self.pipeline.start(config)
            self.camera_type = "RealSense"
            self.start_realsense_thread()
            self.status_bar.config(text="RealSense camera initialized successfully")
            self.status_label.config(text="Status: RealSense Ready")
            print("RealSense camera initialized successfully")
            return True
            
        except Exception as e:
            print(f"RealSense initialization failed: {str(e)}")
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except:
                    pass
                self.pipeline = None
            return False
    
    def try_regular_camera(self):
        """Try to initialize regular camera"""
        try:
            print("Trying regular camera...")
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Regular camera not available")
                return False
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera_type = "Regular Camera"
            self.start_regular_camera_thread()
            self.status_bar.config(text="Regular camera initialized successfully")
            self.status_label.config(text="Status: Camera Ready")
            print("Regular camera initialized successfully")
            return True
            
        except Exception as e:
            print(f"Regular camera initialization failed: {str(e)}")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            return False
    
    def start_demo_mode(self):
        """Start demo mode"""
        print("Starting demo mode...")
        self.camera_type = "Demo Mode"
        self.start_demo_thread()
        self.status_bar.config(text="Demo mode - No camera available")
        self.status_label.config(text="Status: Demo Mode")
    
    def start_demo_thread(self):
        """Start demo thread"""
        self.stop_threads = False
        self.frame_thread = threading.Thread(target=self.update_demo_frame)
        self.frame_thread.daemon = True
        self.frame_thread.start()
    
    def start_realsense_thread(self):
        """Start RealSense camera thread"""
        self.stop_threads = False
        self.frame_thread = threading.Thread(target=self.update_realsense_frame)
        self.frame_thread.daemon = True
        self.frame_thread.start()
    
    def start_regular_camera_thread(self):
        """Start regular camera thread"""
        self.stop_threads = False
        self.frame_thread = threading.Thread(target=self.update_regular_camera_frame)
        self.frame_thread.daemon = True
        self.frame_thread.start()
    
    def update_regular_camera_frame(self):
        """Update regular camera frame continuously"""
        while not self.stop_threads:
            if self.cap:
                try:
                    ret, frame = self.cap.read()
                    if ret:
                        self.process_frame(frame)
                    else:
                        print("Failed to read frame from camera")
                        time.sleep(0.1)
                except Exception as e:
                    print(f"Regular camera frame error: {str(e)}")
                    time.sleep(0.1)
            
            time.sleep(0.03)  # ~33fps
    
    def safe_update_camera_label(self, imgtk):
        """Safely update the camera label from any thread"""
        try:
            self.root.after(0, self._update_camera_label, imgtk)
        except:
            pass
    
    def _update_camera_label(self, imgtk):
        """Update camera label on main thread"""
        try:
            self.camera_label.imgtk = imgtk
            self.camera_label.config(image=imgtk, text="")
        except:
            pass
    
    def detect_basketball(self, img):
        """Detect basketball using color filtering and contour detection, excluding contours in the top-left."""
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Create mask using current HSV values
        lower = np.array([self.hsvVals['hmin'], self.hsvVals['smin'], self.hsvVals['vmin']])
        upper = np.array([self.hsvVals['hmax'], self.hsvVals['smax'], self.hsvVals['vmax']])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Morphological operations to clean mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Define exclusion zone dimensions (in pixels)
        exclusion_width = 0  # Adjust as needed
        exclusion_height = 0  # Adjust as needed
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter out contours in the exclusion zone
        valid_contours = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if x + w > exclusion_width or y + h > exclusion_height:
                valid_contours.append(contour)
        
        if valid_contours:
            # Find the largest valid contour
            largest_contour = max(valid_contours, key=cv2.contourArea)
            
            if cv2.contourArea(largest_contour) > 50:  # Minimum area threshold
                # Get center
                M = cv2.moments(largest_contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    return (cx, cy), mask
        
        return None, mask

    
    def draw_trajectory(self, img):
        """Draw the trajectory on the image"""
        if len(self.posListX) < 2:
            return
        
        # Draw trajectory points and lines
        for i in range(len(self.posListX)):
            pos = (self.posListX[i], self.posListY[i])
            cv2.circle(img, pos, 6, (0, 255, 0), cv2.FILLED)
            
            if i > 0:
                prev_pos = (self.posListX[i-1], self.posListY[i-1])
                cv2.line(img, prev_pos, pos, (0, 255, 0), 2)
        
        # Show ball count and status
        if len(self.posListX) > 0:
            cv2.putText(img, f"Points: {len(self.posListX)}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            if self.is_capturing:
                cv2.putText(img, "TRACKING...", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            
    
    
    
    def update_realsense_frame(self):
        """Update RealSense camera frame continuously"""
        while not self.stop_threads:
            if self.pipeline:
                try:
                    frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                    color_frame = frames.get_color_frame()
                    
                    if not color_frame:
                        continue
                    
                    color_image = np.asanyarray(color_frame.get_data())
                    self.process_frame(color_image)
                    
                except Exception as e:
                    print(f"RealSense frame error: {str(e)}")
                    time.sleep(0.1)
            
            time.sleep(0.03)  # ~33fps
    
    def process_frame(self, color_image):
        """Process frame for ball detection and display"""
        try:
            # Detect basketball
            ball_pos, mask = self.detect_basketball(color_image)
            
            if ball_pos and self.is_capturing:
                # Add to trajectory
                self.posListX.append(ball_pos[0])
                self.posListY.append(ball_pos[1])
                
                # Limit trajectory length for performance
                if len(self.posListX) > 100:
                    self.posListX = self.posListX[-50:]
                    self.posListY = self.posListY[-50:]
                
                # Update detection status
                self.ball_detected = True
                self.root.after(0, self.update_detection_display, True)
            else:
                if self.is_capturing:
                    self.ball_detected = False
                    self.root.after(0, self.update_detection_display, False)
            
            
            
            # Draw trajectory
            self.draw_trajectory(color_image)
            
            # Convert and display
            img = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (800, 450))
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.safe_update_camera_label(imgtk)
            
        except Exception as e:
            print(f"Frame processing error: {str(e)}")
    
    def update_detection_display(self, detected):
        """Update detection display on main thread"""
        try:
            if detected:
                self.detection_label.config(text="🏀 Ball Detected!", foreground="green")
            else:
                self.detection_label.config(text="⚫ No Ball Detected", foreground="red")
        except:
            pass
    
    def update_demo_frame(self):
        """Demo mode with simulated basketball trajectory"""
        width, height = 640, 480
        start_time = time.time()
        
        while not self.stop_threads:
            try:
                img = np.zeros((height, width, 3), dtype=np.uint8)
                
                # Create gradient background
                for y in range(height):
                    for x in range(width):
                        img[y, x] = [int(64 + 32 * np.sin(x/100)), 
                                   int(64 + 32 * np.sin(y/100)), 
                                   int(32 + 16 * np.sin((x+y)/150))]
                
                if self.is_capturing:
                    current_time = time.time()
                    t = (current_time - start_time) % 4  # 4 second cycle
                    
                    # More realistic basketball trajectory
                    ball_x = int(width * (0.1 + 0.8 * t/4))
                    # Parabolic motion with gravity
                    normalized_t = t/4
                    ball_y = int(height * (0.8 - 0.6 * (4 * normalized_t * (1 - normalized_t))))
                    
                    # Add to trajectory lists for demo
                    if len(self.posListX) == 0 or abs(ball_x - self.posListX[-1]) > 5:
                        self.posListX.append(ball_x)
                        self.posListY.append(ball_y)
                        
                        if len(self.posListX) > 30:
                            self.posListX = self.posListX[-20:]
                            self.posListY = self.posListY[-20:]
                    
                    # Draw ball
                    cv2.circle(img, (ball_x, ball_y), 12, (0, 140, 255), -1)
                    cv2.circle(img, (ball_x, ball_y), 12, (255, 255, 255), 2)
                    
                    # Update detection status
                    self.ball_detected = True
                    self.root.after(0, self.update_detection_display, True)
                else:
                    if len(self.posListX) == 0:  # Only reset if no data captured
                        start_time = time.time()
                    self.ball_detected = False
                    self.root.after(0, self.update_detection_display, False)
                
                
                
                # Draw trajectory
                self.draw_trajectory(img)
                
                # Add demo text
                cv2.putText(img, "DEMO MODE - NO CAMERA", (50, height - 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Convert and display
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (800, 450))
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.safe_update_camera_label(imgtk)
                
            except Exception as e:
                print(f"Demo frame error: {str(e)}")
            
            time.sleep(0.05)
    
    def reset_trajectory(self):
        """Reset trajectory data"""
        self.posListX = []
        self.posListY = []
        self.trajectory = []
        self.ball_detected = False
        self.detection_label.config(text="No ball detected", foreground="black")
        self.trajectory_text.delete(1.0, tk.END)
        self.save_button.config(state=tk.DISABLED)
    
    def display_trajectory(self):
        """Display trajectory data"""
        self.trajectory_text.delete(1.0, tk.END)
        
        if not self.posListX:
            self.trajectory_text.insert(tk.END, "No trajectory data captured.")
            return
        
        self.trajectory_text.insert(tk.END, f"Captured {len(self.posListX)} points\n")
        
        # Show sample points
        for i in range(min(10, len(self.posListX))):
            x, y = self.posListX[i], self.posListY[i]
            self.trajectory_text.insert(tk.END, f"Point {i}: ({x}, {y})\n")
        
        if len(self.posListX) > 10:
            self.trajectory_text.insert(tk.END, f"... and {len(self.posListX) - 10} more points")
    
    def save_data(self):
        """Save trajectory and parameters to CSV file"""
        if not self.posListX:
            messagebox.showwarning("No Data", "No trajectory data to save.")
            return
        
        try:
            # Prepare trajectory data
            trajectory_data = list(zip(self.posListX, self.posListY))
            
            data = {
                "Position P": int(self.params["position_p"].get()),
                "Velocity P": int(self.params["velocity_p"].get()),
                "Frequency (Hz)": int(self.params["frequency"].get()),
                "Velocity Cutoff (Hz)": int(self.params["velocity_cutoff"].get()),
                "Battery": self.params["battery"].get(),
                "Battery Voltage": float(self.params["voltage"].get()),
                "Temperature": self.params["temperature"].get(),
                "Start Angle": float(self.params["start_angle"].get()),
                "Shoot Angle": float(self.params["shoot_angle"].get()),
                "Velocity": float(self.params["velocity"].get()),
                "Acceleration": int(self.params["acceleration"].get()),
                "Distance (m)": float(self.params["distance"].get()),
                "Trajectory Points": len(self.posListX),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Trajectory Data": json.dumps(trajectory_data)
            }
            # Save to CSV file with better error handling
            try:
                # Use absolute path for the data file
                data_file_path = os.path.abspath(self.data_file)
                
                # Check if file exists and read existing data
                if os.path.exists(data_file_path):
                    try:
                        existing_df = pd.read_csv(data_file_path)
                    except pd.errors.EmptyDataError:
                        existing_df = pd.DataFrame()
                else:
                    existing_df = pd.DataFrame()
                
                # Create new DataFrame from current data
                new_df = pd.DataFrame([data])
                
                # Concatenate with existing data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Save the combined DataFrame
                combined_df.to_csv(data_file_path, index=False)
                
                messagebox.showinfo("Success", f"Data saved to {data_file_path}")
                self.status_bar.config(text=f"Data saved at {datetime.now().strftime('%H:%M:%S')}")
                self.save_button.config(state=tk.DISABLED)
                print(f"Data successfully saved to {data_file_path}")
                
            except Exception as save_error:
                print(f"CSV save failed: {str(save_error)}")
                # Print full traceback for debugging
                import traceback
                traceback.print_exc()
                messagebox.showerror("Save Error", f"Failed to save data: {str(save_error)}\nCheck console for details.")
                
        except ValueError as e:
            messagebox.showerror("Input Error", f"Please check your input values: {str(e)}")
        except Exception as e:
            messagebox.showerror("Unexpected Error", f"An error occurred while saving: {str(e)}")
            import traceback
            traceback.print_exc()
    
   
    
    def check_create_file(self):
        """Check if CSV data file exists, create headers if not"""
        if not os.path.exists(self.data_file):
            headers = [
                "Position P", "Velocity P", "Frequency (Hz)", "Velocity Cutoff (Hz)",
                "Battery", "Battery Voltage", "Temperature", "Start Angle",
                "Shoot Angle", "Velocity", "Acceleration", "Distance (m)",
                 "Trajectory Points", "Timestamp", "Trajectory Data"
            ]
            
            try:
                # Create CSV with headers
                df = pd.DataFrame(columns=headers)
                df.to_csv(self.data_file, index=False)
                print(f"Created new CSV file: {self.data_file}")
            except Exception as e:
                print(f"Failed to create CSV file: {str(e)}")
    
    def reset_form(self):
        """Reset form"""
        self.shot_result_var.set("silent_shot")
        self.reset_trajectory()
        self.trajectory_text.delete(1.0, tk.END)
        self.trajectory_text.insert(tk.END, "Form reset - ready for new capture.")
        self.save_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Ready")
        self.status_bar.config(text="Form reset")
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.stop_threads = True
            time.sleep(0.2)
            
            if self.pipeline and REALSENSE_AVAILABLE:
                try:
                    self.pipeline.stop()
                except:
                    pass
            
            if hasattr(self, 'cap') and self.cap:
                try:
                    self.cap.release()
                except:
                    pass
            
            try:
                cv2.destroyAllWindows()
            except:
                pass
            
            self.root.destroy()
            sys.exit()

# Main application
if __name__ == "__main__":
    root = tk.Tk()
    app = BasketballTrackingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()