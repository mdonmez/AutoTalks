import torch
if torch.cuda.is_available():
    print("CUDA is available")
    print(f"There are {torch.cuda.device_count()} CUDA devices available")
    print(f"The system will use device at index {torch.cuda.current_device()}")
    print(f"The current device for CUDA is {torch.cuda.get_device_name(torch.cuda.current_device())}")
else:
    print("CUDA is not available. Please look at INSTALLATION.MD for installation instructions.")