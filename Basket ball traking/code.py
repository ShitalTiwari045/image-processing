import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, Label, Button, ttk, StringVar
from scipy.interpolate import splprep, splev
import ast

# Load the dataset
file_path = '/home/dharm/Desktop/basketball_traj_data.csv'
data = pd.read_csv(file_path)

def smooth_trajectory(x, y, smoothing=3):
    """Smooths the trajectory using spline interpolation."""
    try:
        tck, u = splprep([x, y], s=smoothing)
        x_smooth, y_smooth = splev(u, tck)
        return x_smooth, y_smooth
    except Exception as e:
        print(f"Error during spline smoothing: {e}")
        return x, y  # Return original data if smoothing fails

def plot_trajectory(index):
    """Plots the smoothed trajectory with flipped y-coordinates."""
    try:
        # Parse trajectory data
        trajectory_str = data.loc[index, "Trajectory Data"]
        trajectory = ast.literal_eval(trajectory_str)
        if len(trajectory) < 2:
            print(f"Trajectory {index} is too short for visualization.")
            return
        x, y = zip(*trajectory)  # Separate x and y coordinates
        y = [-coord for coord in y]  # Flip the y-coordinates

        # Smooth the trajectory
        x_smooth, y_smooth = smooth_trajectory(x, y)

        # Plotting
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, 'o', label="Original Data", alpha=0.5)
        plt.plot(x_smooth, y_smooth, '-', label="Smoothed Trajectory")
        plt.title(f"Trajectory {index + 1} (Smoothed, Flipped Y)")
        plt.xlabel("X Coordinate")
        plt.ylabel("Y Coordinate")
        plt.legend()
        plt.grid()
        plt.show()
    except Exception as e:
        print(f"An error occurred while plotting trajectory {index}: {e}")

def on_select(event):
    """Callback for dropdown menu selection."""
    selected_index = dropdown_var.get()
    if selected_index.isdigit():
        plot_trajectory(int(selected_index))
    else:
        print("Invalid selection. Please select a valid index.")

# Create the main GUI window
root = Tk()
root.title("Trajectory Data Analyzer")

# Dropdown menu for selecting trajectory
Label(root, text="Select Trajectory:").grid(row=0, column=0, padx=10, pady=10)
dropdown_var = StringVar()
dropdown = ttk.Combobox(root, textvariable=dropdown_var)
dropdown["values"] = [str(idx) for idx in range(len(data))]
dropdown.grid(row=0, column=1, padx=10, pady=10)

# Bind selection event
dropdown.bind("<<ComboboxSelected>>", on_select)

# Exit button
Button(root, text="Exit", command=root.quit).grid(row=1, column=1, padx=10, pady=10)

# Run the GUI loop
root.mainloop()
