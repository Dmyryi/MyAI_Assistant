"""Frame and segment storage repository"""
import os
import json
from typing import List
from dataclasses import asdict
from domain import IFrameRepository, VisualFrame, VideoSegment


class VisualFrameRepository(IFrameRepository):
    """Manages persistence of frames and segments"""
    
    def __init__(self, db_file: str = "data/visual_db.json", segments_db_file: str = "data/segments_db.json"):
        self.db_file = db_file
        self.segments_db_file = segments_db_file
        self.db_dir = os.path.dirname(db_file)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Creates database directory if it doesn't exist"""
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
    
    def save(self, frames: List[VisualFrame]) -> None:
        """Saves frames to JSON file"""
        all_data = []
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                all_data = []
        
        for frame in frames:
            all_data.append(asdict(frame))
        
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def load_all(self) -> List[VisualFrame]:
        """Loads all frames from JSON file"""
        if not os.path.exists(self.db_file):
            return []
        
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [VisualFrame(**item) for item in data]
        except (json.JSONDecodeError, IOError, TypeError):
            return []
    
    def prune_missing(self) -> int:
        """Removes records of non-existent files"""
        if not os.path.exists(self.db_file):
            return 0
        
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return 0
        
        original_len = len(data)
        filtered = [
            item for item in data 
            if item.get("frame_path") and os.path.exists(item["frame_path"])
        ]
        removed = original_len - len(filtered)
        
        if removed > 0:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False, indent=2)
            self._cleanup_empty_dirs()
        
        return removed
    
    def _cleanup_empty_dirs(self) -> None:
        """Cleans up empty frame directories"""
        frames_dir = "data/frames"
        if not os.path.exists(frames_dir):
            return
        
        for root, dirs, files in os.walk(frames_dir, topdown=False):
            if not dirs and not files:
                try:
                    os.rmdir(root)
                except OSError:
                    pass
    
    def save_segments(self, segments: List[VideoSegment]) -> None:
        """Saves segments to JSON file"""
        all_data = []
        if os.path.exists(self.segments_db_file):
            try:
                with open(self.segments_db_file, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                all_data = []
        
        for segment in segments:
            segment_dict = {
                "video_filename": segment.video_filename,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "segment_id": segment.segment_id,
                "preview_frame_path": segment.preview_frame_path,
                "key_frames": [asdict(frame) for frame in segment.key_frames]
            }
            all_data.append(segment_dict)
        
        with open(self.segments_db_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def load_all_segments(self) -> List[VideoSegment]:
        """Loads all segments from JSON file"""
        if not os.path.exists(self.segments_db_file):
            return []
        
        try:
            with open(self.segments_db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            segments = []
            for item in data:
                key_frames = [
                    VisualFrame(**frame_dict) 
                    for frame_dict in item.get("key_frames", [])
                ]
                
                segment = VideoSegment(
                    video_filename=item["video_filename"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    segment_id=item["segment_id"],
                    preview_frame_path=item["preview_frame_path"],
                    key_frames=key_frames
                )
                segments.append(segment)
            
            return segments
        except (json.JSONDecodeError, IOError, TypeError, KeyError) as e:
            print(f"Ошибка загрузки сегментов: {e}")
            return []

