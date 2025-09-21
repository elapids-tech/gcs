class DroneSettings:
    def __init__(self, drone_id: int = -1, ip_address: str = None):
        self.drone_id = drone_id
        self.ip_address = ip_address
        self.bin_threshold = 128  # Default threshold for binary conversion

    def set_drone_id(self, drone_id: int):
        if drone_id >= 0:
            self.drone_id = drone_id
        else:
            raise ValueError("Drone ID must be a non-negative integer.")
        
    def set_ip_address(self, ip_address: str):
        self.ip_address = ip_address
        
    def set_bin_threshold(self, threshold: int):
        if 0 <= threshold <= 255:
            self.bin_threshold = threshold
        else:
            raise ValueError("Threshold must be between 0 and 255.")
    
