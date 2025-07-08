#!/bin/bash

# Input directory (current directory by default)
INPUT_DIR="./chopped_videos"
# Output directory (will maintain same subdir structure)
OUTPUT_DIR="./compressed_videos"

# Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input directory '$INPUT_DIR' does not exist!"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Find all video files (common extensions) recursively
find "$INPUT_DIR" -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.flv" -o -iname "*.webm" \) | while read -r input_file; do
    # Check if input file exists before processing
    if [ ! -f "$input_file" ]; then
        echo "Warning: Input file '$input_file' does not exist, skipping..."
        continue
    fi
    
    # Get the relative path (to preserve subdir structure)
    rel_path="${input_file#$INPUT_DIR/}"
    # Create output path
    output_file="$OUTPUT_DIR/$rel_path"
    # Create subdirectories in output if they don't exist
    mkdir -p "$(dirname "$output_file")"
    
    echo "Compressing: $input_file"
    
    # FFmpeg command (adjust settings as needed)
    if ffmpeg -i "$input_file" \
        -vf "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease" \
        -c:v libx264 \
        -crf 23 \
        -preset slow \
        -c:a aac \
        -b:a 128k \
        -movflags +faststart \
        "$output_file"; then
        echo "Successfully saved to: $output_file"
    else
        echo "Error: Failed to compress '$input_file'"
    fi
done

echo "Compression complete! Check $OUTPUT_DIR"
