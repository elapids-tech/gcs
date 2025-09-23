class DroneSettings:
    def __init__(self):
        self.bin_threshold = 128  # Default threshold for binary conversion

    def set_bin_threshold(self, threshold: int):
        if 0 <= threshold <= 255:
            self.bin_threshold = threshold
        else:
            raise ValueError("Threshold must be between 0 and 255.")
    
