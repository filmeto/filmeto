"""
OpenCV utilities module for image and video processing operations.
Provides methods for extracting frames from videos using OpenCV as a fallback.
"""
import os
from pathlib import Path
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


def extract_last_frame_opencv(video_path: Union[str, Path], output_path: Union[str, Path]) -> Optional[str]:
    """
    Extract the last frame from a video using OpenCV as a fallback when FFmpeg is not available.
    
    Args:
        video_path: Path to the input video file
        output_path: Path where the extracted frame will be saved
        
    Returns:
        str: Path to the saved image if successful, None if failed
    """
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'")
        return None
    
    try:
        # Open the video to get the last frame
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            # Get total frame count
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames > 0:
                # Set to the last frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
                ret, frame = cap.read()
                
                if ret:
                    # Save the last frame to the specified output path
                    success = cv2.imwrite(str(output_path), frame)
                    
                    if success:
                        logger.info(f"Saved last frame with OpenCV as: {output_path}")
                        cap.release()
                        return str(output_path)
                    else:
                        logger.error("Failed to save the extracted frame with OpenCV")
                else:
                    logger.error("Failed to read the last frame from video with OpenCV")
            else:
                logger.error("Video has no frames")
        else:
            logger.error("Failed to open video file with OpenCV")
        
        cap.release()
    except Exception as e:
        logger.error(f"Exception occurred in OpenCV frame extraction: {e}", exc_info=True)

    # Return None if OpenCV method fails
    return None


def extract_first_frame_opencv(video_path: Union[str, Path], output_path: Union[str, Path]) -> Optional[str]:
    """
    Extract the first frame from a video using OpenCV.
    
    Args:
        video_path: Path to the input video file
        output_path: Path where the extracted frame will be saved
        
    Returns:
        str: Path to the saved image if successful, None if failed
    """
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'")
        return None
    
    try:
        # Open the video to get the first frame
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            # Read the first frame
            ret, frame = cap.read()
            
            if ret:
                # Save the first frame
                success = cv2.imwrite(str(output_path), frame)
                
                if success:
                    logger.info(f"Saved first frame with OpenCV as: {output_path}")
                    cap.release()
                    return str(output_path)
                else:
                    logger.error("Failed to save the extracted first frame with OpenCV")
            else:
                logger.error("Failed to read the first frame from video with OpenCV")
        else:
            logger.error("Failed to open video file with OpenCV")
        
        cap.release()
    except Exception as e:
        logger.error(f"Exception occurred in OpenCV first frame extraction: {e}", exc_info=True)

    # Return None if OpenCV method fails
    return None


def get_video_duration(video_path: Union[str, Path]) -> Optional[float]:
    """
    Get the duration of a video file in seconds using OpenCV.
    
    Args:
        video_path: Path to the input video file
        
    Returns:
        float: Duration in seconds if successful, None if failed
    """
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'")
        return None
    
    try:
        # Open the video
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps > 0 and frame_count > 0:
                # Calculate duration
                duration = frame_count / fps
                cap.release()
                logger.info(f"Video duration: {duration}s (frames: {frame_count}, fps: {fps})")
                return duration
            else:
                logger.error("Could not get FPS or frame count from video")
        else:
            logger.error("Failed to open video file with OpenCV")
        
        cap.release()
    except Exception as e:
        logger.error(f"Exception occurred while getting video duration: {e}", exc_info=True)

    return None


def extract_frame_at_time_opencv(video_path: Union[str, Path], output_path: Union[str, Path], 
                                time_seconds: float) -> Optional[str]:
    """
    Extract a frame at a specific time from a video using OpenCV.
    
    Args:
        video_path: Path to the input video file
        output_path: Path where the extracted frame will be saved
        time_seconds: Time in seconds to extract the frame at
        
    Returns:
        str: Path to the saved image if successful, None if failed
    """
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'")
        return None
    
    try:
        # Open the video
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            # Get video FPS
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps > 0:
                # Calculate frame number for the given time
                frame_number = int(time_seconds * fps)
                
                # Set to the specified frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if ret:
                    # Save the frame
                    success = cv2.imwrite(str(output_path), frame)
                    
                    if success:
                        logger.info(f"Saved frame at {time_seconds}s with OpenCV as: {output_path}")
                        cap.release()
                        return str(output_path)
                    else:
                        logger.error(f"Failed to save frame at {time_seconds}s with OpenCV")
                else:
                    logger.error(f"Failed to read frame at {time_seconds}s from video with OpenCV")
            else:
                logger.error("Could not get FPS from video")
        else:
            logger.error("Failed to open video file with OpenCV")
        
        cap.release()
    except Exception as e:
        logger.error(f"Exception occurred in OpenCV time-based frame extraction: {e}", exc_info=True)

    # Return None if OpenCV method fails
    return None