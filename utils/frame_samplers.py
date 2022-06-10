

#%% Imports

import numpy as np


#%%

class Randomized_Frame_Sampler:
    
    '''
    Class used sample frames from a video with randomized cropping offsets, as well as
    randomizing the time interval over which sampling is performed. Intended to be
    used to help provide frames for an 'auto-generated' background that appears shifted.
    Example usage:
        
        # Assume an OpenCV cv2.VideoCapture(...) has been set up & video properties are known
        vread = cv2.VideoCapture(...)
        
        # Instantiate sampler
        sampler = Randomized_Frame_Sampler(...)
        
        # Sample frames from video
        cropped_samples_list = []
        for each_random_sample_idx in sampler.get_frame_indices():
            vread.set(cv2.CAP_PROP_POS_FRAMES, each_sample_idx)
            rec_frame, frame = vread.read()
            new_cropped_frame = each_bg_sampler.crop(frame)
            cropped_samples_list.append(new_cropped_frame)
    '''
    
    def __init__(self, video_wh, max_shift_xy, min_max_sampling_duration, num_samples = 15):
        
        # Store inputs
        self._video_width, self._video_height = video_wh
        self._max_x_shift, self._max_y_shift = max_shift_xy
        self._min_duration, self._max_duration = sorted(min_max_sampling_duration)
        self._num_samples = num_samples
        
        # Pre-calculate random crop & sampling values, so we don't re-randomize each time we need them!
        self._crop_y1y2x1x2 = self._get_randomized_crop_coords()
        self._norm_sample_idxs = self._get_randomized_norm_sampling_indices()
    
    def disable_random_shift(self):
        
        ''' Special function used to center cropping to use as a 'reference' image '''
        
        output_width = self._video_width - self._max_x_shift
        output_height = self._video_height - self._max_y_shift
        
        crop_x1 = int(self._max_x_shift / 2)
        crop_y1 = int(self._max_y_shift / 2)
        crop_x2 = int(crop_x1 + output_width)
        crop_y2 = int(crop_y1 + output_height)
        
        self._crop_y1y2x1x2 = (crop_y1, crop_y2, crop_x1, crop_x2)
    
    def disable_random_sample_timing(self):
        
        ''' Special function used to turn off randomized sampling (so that entire video is considered) '''
        
        self._min_duration = self._max_duration = 1.0
        self._norm_sample_idxs = self._get_randomized_norm_sampling_indices()
    
    def crop(self, frame):
        
        ''' Helper function for cropping full-frame data '''
        
        # For convenience
        crop_y1, crop_y2, crop_x1, crop_x2 = self._crop_y1y2x1x2      
        
        return frame[crop_y1:crop_y2, crop_x1:crop_x2]
    
    def get_xy_shift(self):
        
        '''
        Returns the (relative) amount of xy shifting due to randomly selected crop co-ordinates,
        assuming a centered crop corresponds to an xy shift of (0, 0)
        '''
        
        # Calculated co-ords. corresponding to a center crop
        centered_x = int(self._max_x_shift / 2)
        centered_y = int(self._max_y_shift / 2)
        
        # Calculate shift as the relative difference between actual crop and a centered crop
        crop_y1, _, crop_x1, _ = self._crop_y1y2x1x2
        x_shift = crop_x1 - centered_x
        y_shift = crop_y1 - centered_y
        
        return x_shift, y_shift
    
    def get_frame_indices(self, total_video_frames):
        ''' Get (integer) frame index values to sample from '''
        return np.int32(np.round((total_video_frames - 1) * self._norm_sample_idxs))
    
    def _get_randomized_crop_coords(self):
        
        '''
        Function used to generate random shifted cropping co-ordinates
        Randomization occurs in only the top-left crop point, with the width/height of the
        cropped result being fixed
        '''
        
        # Determine where to crop from
        output_width = self._video_width - self._max_x_shift
        output_height = self._video_height - self._max_y_shift
        crop_x1 = np.random.randint(0, self._max_x_shift + 1)
        crop_y1 = np.random.randint(0, self._max_y_shift + 1)
        crop_x2 = int(crop_x1 + output_width)
        crop_y2 = int(crop_y1 + output_height)
        
        crop_y1y2x1x2 = (crop_y1, crop_y2, crop_x1, crop_x2)
        
        return crop_y1y2x1x2
    
    def _get_randomized_norm_sampling_indices(self):
        
        '''
        Function used to generate randomized indices to sample from (in 0-to-1 normalized values)
        Randomization occurs in the timing of the first & last samples (and therefore duration of sampling),
        with all samples in-between being evenly spaced
        '''
        
        # Decide on a (randomized) duration to sample over
        norm_sample_duration = self._min_duration + (self._max_duration - self._min_duration) * np.random.rand()
        
        # Decide on a (also randomized) start/end time for sampling
        earliest_norm_sample = (1.0 - norm_sample_duration) * np.random.rand()
        latest_norm_sample = earliest_norm_sample + norm_sample_duration
        
        # Generate normalized sample timing
        norm_sample_idxs = np.linspace(earliest_norm_sample, latest_norm_sample, self._num_samples)
        
        return norm_sample_idxs


#%% Demo

if __name__ == "__main__":
    pass
