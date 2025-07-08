import os
import cv2
from pathlib import Path

def process_videos_and_images():
    videos_dir = Path("videos")
    output_dir = Path("chopped_videos")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Process each subdirectory in videos
    for subdir in videos_dir.iterdir():
        if not subdir.is_dir():
            continue
            
        # Create corresponding output subdirectory
        output_subdir = output_dir / subdir.name
        output_subdir.mkdir(exist_ok=True)
        
        # Get all video files (MOV and MP4)
        video_extensions = {'.mov', '.mp4'}
        video_files = [f for f in subdir.iterdir() 
                      if f.suffix.lower() in video_extensions]
        
        # Get all image files (JPG and PNG)
        image_extensions = {'.jpg', '.jpeg', '.png'}
        image_files = [f for f in subdir.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        # Process videos
        for i, video_file in enumerate(video_files, 1):
            chop_video(video_file, output_subdir, i)
        
        # Process images
        for i, image_file in enumerate(image_files, 1):
            create_video_from_image(image_file, output_subdir, len(video_files) + i)

def chop_video(video_path, output_dir, start_index):
    """Chop video into 5-second clips"""
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 5 seconds worth of frames
    frames_per_clip = fps * 5
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    clip_number = start_index
    frame_count = 0
    out = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Start new clip every 5 seconds
        if frame_count % frames_per_clip == 0:
            if out is not None:
                out.release()
            output_path = output_dir / f"{clip_number}.mp4"
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))
            clip_number += 1
        
        if out is not None:
            out.write(frame)
        frame_count += 1
    
    if out is not None:
        out.release()
    cap.release()

def create_video_from_image(image_path, output_dir, index):
    """Create a 5-second video from an image"""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error reading image: {image_path}")
        return
    
    height, width = img.shape[:2]
    fps = 30  # 30 fps for smooth playback
    duration = 5  # 5 seconds
    total_frames = fps * duration
    
    output_path = output_dir / f"{index}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Write the same frame for 5 seconds
    for _ in range(total_frames):
        out.write(img)
    
    out.release()

if __name__ == "__main__":
    process_videos_and_images()