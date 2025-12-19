"""Video indexing service"""
import os
from typing import List
from domain import IVideoIndexer, IFrameRepository, VisualFrame, VideoSegment
from infrastructure.localization import _

class VideoIndexingService:
    """Manages video indexing process"""
    
    def __init__(
        self,
        indexer: IVideoIndexer,
        repository: IFrameRepository,
        video_folder: str = "source_videos"
    ):
        self.indexer = indexer
        self.repository = repository
        self.video_folder = os.path.abspath(video_folder)
        self._ensure_video_folder()
    
    def _ensure_video_folder(self) -> None:
        """Creates video folder if it doesn't exist"""
        if not os.path.exists(self.video_folder):
            os.makedirs(self.video_folder)
    
    def get_indexed_files(self) -> set:
        """Returns set of already indexed video files"""
        frames = self.repository.load_all()
        segments = self.repository.load_all_segments()
        frame_files = {frame.video_filename for frame in frames}
        segment_files = {segment.video_filename for segment in segments}
        return frame_files | segment_files
    
    def index_new_videos(self) -> int:
        """Indexes new videos from folder"""
        removed = self.repository.prune_missing()
        if removed > 0:
            print(_("video_indexing_pruned", count=removed))
        
        processed_files = self.get_indexed_files()
        
        try:
            files_on_disk = [
                f for f in os.listdir(self.video_folder) 
                if f.endswith(('.mp4', '.mov', '.mkv'))
            ]
        except OSError as e:
             files_on_disk = []

        new_files = [f for f in files_on_disk if f not in processed_files]
        
        if not new_files:
            print(_("video_indexing_index_actual"))
            return 0
        
        print(_("video_indexing_new_videos_found", count=len(new_files)))
        success_count = 0
        
        for filename in new_files:
            full_path = os.path.join(self.video_folder, filename)
            try:
                segments = self.indexer.extract_segments(full_path)
                if segments:
                    self.repository.save_segments(segments)
                    print(_("video_indexing_added_to_db", filename=filename))
                    success_count += 1
                else:
                    frames = self.indexer.extract_frames(full_path)
                    if frames:
                        self.repository.save(frames)
                        print(_("video_indexing_added_to_db", filename=filename))
                        success_count += 1
            except Exception as e:
                print(_("video_indexing_error_with_file", filename=filename, error=e))
                import traceback
                traceback.print_exc()
        
        return success_count