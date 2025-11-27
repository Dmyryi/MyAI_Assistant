"""Single Responsibility: Индексация видео и извлечение кадров"""
import os
import re
import cv2
# Імпорти для детекції сцен
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from typing import List

from domain.interfaces import IVideoIndexer
from domain.entities import VisualFrame

# --- ВАЖЛИВО: Використовуємо стандартний імпорт _ ---
from infrastructure.localization import _
# --------------------------------------------------

class VideoIndexer(IVideoIndexer):
    """Single Responsibility: Извлечение ключевых кадров из видео"""
    
    def __init__(self, frames_dir: str = "data/frames"):
        # Використовуємо абсолютний шлях, щоб точно знати, де папка
        self.frames_dir = os.path.abspath(frames_dir)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Создает директорию для кадров"""
        if not os.path.exists(self.frames_dir):
            try:
                os.makedirs(self.frames_dir)
            except OSError as e:
                # Тут вже використовується _, тому імпорт має бути зверху
                print(_("video_indexer_create_dir_error_crit", error=e))
    
    def _sanitize_filename(self, filename: str) -> str:
        """Очищает имя файла от недопустимых символов"""
        name, ext = os.path.splitext(filename)
        clean_name = re.sub(r'[^\w\s\.\-\']', '_', name)
        clean_name = re.sub(r'[\s_]+', '_', clean_name).strip('_')
        return clean_name + ext
    
    def extract_frames(self, video_path: str, threshold: float = 27.0) -> List[VisualFrame]:
        """Извлекает ключевые кадры из видео"""
        # Ось цей рядок викликав помилку. Тепер конфлікту не буде.
        print(_("video_indexer_analyzing_scenes", video_path=video_path))
        
        video_name = os.path.basename(video_path)
        safe_video_folder_name = self._sanitize_filename(video_name)
        video_frames_dir = os.path.join(self.frames_dir, safe_video_folder_name)
        
        # Создаем поддиректорию для кадров конкретного видео
        if not os.path.exists(video_frames_dir):
            try:
                os.makedirs(video_frames_dir)
            except OSError as e:
                print(_("video_indexer_create_dir_error_crit", error=e))
                return []
        
        frames_data = []
        
        # Этап 1: Обнаружение сцен
        try:
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=threshold))
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager, show_progress=True)
            scene_list = scene_manager.get_scene_list()
            print(_("video_indexer_scenes_found", count=len(scene_list)))
            video_manager.release()
        except Exception as e:
            print(_("video_indexer_scene_detect_error", error=e))
            if 'video_manager' in locals() and video_manager:
                video_manager.release()
            return []
        
        if not scene_list:
            print(_("video_indexer_no_scenes_warning"))
            return []
        
        # Этап 2: Извлечение центрального кадра каждой сцены
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise IOError(_("video_indexer_opencv_open_error", video_path=video_path))
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 24.0 
            
            scene_count = 0
            for i, (start_time, end_time) in enumerate(scene_list):
                start_frame_num = start_time.get_frames()
                end_frame_num = end_time.get_frames()
                middle_frame_num = start_frame_num + int((end_frame_num - start_frame_num) / 2)
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_num)
                success, image = cap.read()
                
                if not success:
                    print(_("video_indexer_read_frame_error", frame_num=middle_frame_num, scene_idx=i))
                    continue
                
                timestamp_sec = middle_frame_num / fps
                frame_filename = os.path.abspath(
                    os.path.join(video_frames_dir, f"scene_{i}_frame_{middle_frame_num}.jpg")
                )
                
                try:
                    # --- КРИТИЧНЕ ВИПРАВЛЕННЯ ---
                    # Використовуємо __ (два підкреслення) для локальної змінної.
                    # Це усуває конфлікт з функцією перекладу _().
                    h, w, __ = image.shape
                    # ----------------------------
                    target_h = 360
                    aspect_ratio = w / h
                    target_w = int(target_h * aspect_ratio)
                    resized_image = cv2.resize(image, (target_w, target_h))
                    
                    if cv2.imwrite(frame_filename, resized_image, [cv2.IMWRITE_JPEG_QUALITY, 85]):
                        if os.path.exists(frame_filename) and os.path.getsize(frame_filename) > 0:
                            frames_data.append(VisualFrame(video_name, timestamp_sec, frame_filename))
                            scene_count += 1
                        else:
                            print(_("video_indexer_save_error", filename=frame_filename))
                    else:
                        print(_("video_indexer_write_error", filename=frame_filename))
                except Exception as e:
                    print(_("video_indexer_process_frame_error", scene_idx=i, error=e))
                    continue
            
            cap.release()
            print(_("video_indexer_success", count=scene_count))
            return frames_data
            
        except Exception as e:
             print(_("video_indexer_scene_detect_error", error=e))
             if 'cap' in locals() and cap.isOpened():
                 cap.release()
             return []