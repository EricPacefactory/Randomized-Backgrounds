

#%% Imports 

import os
import argparse
import cv2
import numpy as np
import easygui as eg

from tqdm import tqdm

from utils.frame_samplers import Randomized_Frame_Sampler


#%% Functions

def cornered_imshow(title, frame):
    cv2.namedWindow(title)
    cv2.moveWindow(title, 50, 50)
    cv2.imshow(title, frame)


#%% Parse script args
    
# Create the parser
ap = argparse.ArgumentParser(description="Create multiple shifted & cropped median backgrounds from a single video")

# Add the arguments
default_output_folder = "results"
default_num_output = 5
default_num_samples = 15
default_x_shift = 100
default_y_shift = default_x_shift
default_min_duration = 0.25
default_max_duration = 1.0

# Build arguments
easy_arg = lambda help_msg, default: {"help": "{} (default is {})".format(help_msg, default), "type": type(default), "default": default}
ap.add_argument("video", metavar = "v", nargs = "?", type = str, help = "Path to input video")
ap.add_argument("-o", "--output", **easy_arg("Path to output folder", default_output_folder))
ap.add_argument("-n", "--num_output", **easy_arg("Number of backgrounds to generate", default_num_output))
ap.add_argument("-s", "--num_samples", **easy_arg("Number of frames to sample per median background", default_num_samples))
ap.add_argument("-x", "--max_x_shift", **easy_arg("Maximum amount to shift in x direction", default_x_shift))
ap.add_argument("-y", "--max_y_shift", **easy_arg("Maximum amount to shift in y direction", default_y_shift))
ap.add_argument("-dn", "--min_sampling_duration", 
                **easy_arg("Minimum fraction of video that samples should be taken from", default_min_duration))
ap.add_argument("-dx", "--max_sampling_duration", 
                **easy_arg("Maximum fraction of video that samples should be taken from", default_max_duration))

# For convenience
ap_result = ap.parse_args()
ARG_VIDEO = ap_result.video
ARG_OUTPUT = ap_result.output
ARG_NUM_OUTPUT = ap_result.num_output
ARG_NUM_SAMPLES = ap_result.num_samples
ARG_MAX_X_SHIFT = ap_result.max_x_shift
ARG_MAX_Y_SHIFT = ap_result.max_y_shift
ARG_MIN_DURATION = ap_result.min_sampling_duration
ARG_MAX_DURATION = ap_result.max_sampling_duration


#%% Input setup

# Get user to provide video path, if not given through script arguments
no_video_arg = (ARG_VIDEO is None)
video_source = eg.fileopenbox(title = "Select a video", default = "~/Desktop/*") if no_video_arg else ARG_VIDEO

# Bail if no video selected
no_video_select = (video_source is None)
if no_video_select:
    print("", "No video selected. Quitting...", "", sep = "\n")
    quit()

# Make sure we can find the input video
if not os.path.exists(video_source):
    print("", "Couldn't find video: {}".format(video_source), sep = "\n")
    quit()

# Set up video reader & get info about video (for sizing generated background image)
vread = cv2.VideoCapture(video_source)
video_width = int(vread.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(vread.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(vread.get(cv2.CAP_PROP_FRAME_COUNT))


#%% Background capture config

# Create multiple background samplers (so we get multiple variants of the background)
video_wh = (video_width, video_height)
max_shift_xy = (ARG_MAX_X_SHIFT, ARG_MAX_Y_SHIFT)
min_max_sampling_duration = (ARG_MIN_DURATION, ARG_MAX_DURATION)
sampler_args = (video_wh, max_shift_xy, min_max_sampling_duration, ARG_NUM_SAMPLES)
bg_samplers_list = [Randomized_Frame_Sampler(*sampler_args) for _ in range(ARG_NUM_OUTPUT)]

# Make 'first' sampler into a reference/centered variant by removing random shifting
bg_samplers_list[0].disable_random_shift()
bg_samplers_list[0].disable_random_sample_timing()


#%% Capture loop

# Some feedback
print("", "Generating {} background images!".format(len(bg_samplers_list)), "", sep = "\n", flush = True)

median_bg_frames = []
try:
    
    # Capture cropped frames for each sample
    for each_bg_sampler in bg_samplers_list:
        
        cropped_samples_list = []
        for each_sample_idx in tqdm(each_bg_sampler.get_frame_indices(total_frames)):
            
            # Read target frame from video
            vread.set(cv2.CAP_PROP_POS_FRAMES, each_sample_idx)
            rec_frame, frame = vread.read()
            if not rec_frame:
                print("Error reading frame @ {:.2f}".format(each_sample_idx), "Skipping...", sep = "\n")
                continue
            
            # Crop video frames for use in generating median later
            new_cropped_frame = each_bg_sampler.crop(frame)
            cropped_samples_list.append(new_cropped_frame)
        
        # Create median background from frames and store (so we can dump cropped data for next iteration!)
        new_median_bg = np.uint8(np.round(np.median(cropped_samples_list, axis = 0)))
        median_bg_frames.append(new_median_bg)

except KeyboardInterrupt:
    print("", "Keyboard cancelled!", "", sep = "\n")

# Clean up
vread.release()


#%% Show/save result

# Show results to user
cornered_imshow("Centered", median_bg_frames[0])
for k, each_bg_frame in enumerate(median_bg_frames[1:]):
    cornered_imshow("BG{}".format(k), each_bg_frame)
cv2.waitKey(250)

# Ask user if they are ok saving results
try:
    user_input = input("Save results? [y]/n ")
    save_confirmed = (user_input.strip().lower() != "n")
except KeyboardInterrupt:
    print("  -> Save cancelled")
    save_confirmed = False

# Wipe out background frames
cv2.destroyAllWindows()

# Write background images to disk if needed
if save_confirmed:
    
    # Construct base folder pathing
    video_file_name = os.path.basename(video_source)
    video_name_only, _ = os.path.splitext(video_file_name)
    video_name_only = video_name_only.strip().lower().replace(" ", "_")
    save_folder_path = os.path.join(os.path.abspath(ARG_OUTPUT), video_name_only)
    os.makedirs(save_folder_path, exist_ok = True)
    
    # Construct save pathing for each background image & save data to disk
    for each_bg_sampler, each_bg_frame in zip(bg_samplers_list, median_bg_frames):
        x_shift, y_shift = each_bg_sampler.get_xy_shift()
        save_name = "({}, {}).png".format(x_shift, y_shift)
        save_path = os.path.join(save_folder_path, save_name)
        cv2.imwrite(save_path, each_bg_frame)
    pass

    # Some feedback
    print("", "Saved data!", "@ {}".format(save_folder_path), sep = "\n")
