"""Document analysis and frame/segment search service"""
from typing import List, Optional, Callable
from domain import IDocumentSource, ISearchEngine, ILogger, ScenarioBlock, VisualFrame, SearchResult, VideoSegment
import traceback


from infrastructure.localization import _

class DocumentAnalysisService:
    """Coordinates document analysis and frame search"""
    
    def __init__(
        self,
        document_source: IDocumentSource,
        search_engine: ISearchEngine,
        logger: Optional[ILogger] = None,
        score_threshold: float = 0.25,
        history_size: int = 15,
        time_window: float = 5.0
    ):
        self.document_source = document_source
        self.search_engine = search_engine
        self.logger = logger
        self.score_threshold = score_threshold
        self.history_size = history_size
        self.time_window = time_window
        self.used_frames_history: List[tuple[str, float]] = []
    
    def analyze_document(
        self,
        document_id: str,
        progress_callback: Optional[Callable[[str, dict], None]] = None
    ) -> List[SearchResult]:
        """Анализирует документ и находит подходящие кадры"""
        if not self.document_source.is_connected():
            self.document_source.connect(document_id)
        
        if not self.search_engine.is_ready():
            raise RuntimeError(_("search_engine_not_ready"))
        
        results = []
        blocks = list(self.document_source.extract_blocks())
        total_blocks = len(blocks)
        
        if progress_callback:
            progress_callback("status", _("analysis_blocks_found", count=total_blocks))
        
        print(_("debug_start_processing_blocks", count=total_blocks))

        for idx, block in enumerate(blocks, 1):
            print(_("debug_block_start", idx=idx, snippet=block.text[:20]))

            if progress_callback:
                progress_callback(
                    "status", 
                    _("analysis_processing_block", idx=idx, total=total_blocks)
                )
            
            try:
                result = self._process_block(block)
                
                if result:
                    results.append(result)
                    if progress_callback:
                        progress_callback("result_found", self._result_to_dict(result))
                
                print(_("debug_block_success", idx=idx))

            except Exception as e:
                print(_("error_critical_on_block", idx=idx))
                print(_("error_message_label", error=e))
                print(_("error_traceback_start"))
                traceback.print_exc()
                print(_("error_traceback_end"))

        print(_("debug_processing_finished"))

        if progress_callback:
            progress_callback("finished", None)
        
        return results

    def _process_block(self, block: ScenarioBlock) -> Optional[SearchResult]:
        """Обрабатывает один блок сценария (Стратегія: Унікальний > Дублікат > Нічого)"""
        block_snippet = block.text[:20] + "..."
        print(_("debug_process_block_start", snippet=block_snippet))
        
        segment_results = self.search_engine.search_segments(block.text, limit=12)
        
        if segment_results:
            return self._process_segment_results(block, segment_results, block_snippet)
        
        search_results = self.search_engine.search(block.text, limit=12)
        
        if not search_results:
             print(_("debug_neural_found_nothing", snippet=block_snippet))
             return None

        absolute_best_frame, absolute_best_score = search_results[0]
        print(_("debug_plan_b_candidate", snippet=block_snippet, filename=absolute_best_frame.video_filename, score=absolute_best_score))

        unique_frame = None
        unique_score = 0.0
        
        for frame, score in search_results:
            if score < self.score_threshold:
                break 
            
            if not self._is_duplicate(frame):
                unique_frame = frame
                unique_score = score
                print(_("debug_unique_found", snippet=block_snippet, score=score))
                break

        final_frame = None
        final_score = 0.0
        took_duplicate = False

        if unique_frame:
            final_frame = unique_frame
            final_score = unique_score
        elif absolute_best_score >= self.score_threshold:
            final_frame = absolute_best_frame
            final_score = absolute_best_score
            took_duplicate = True
            print(_("debug_taking_duplicate", snippet=block_snippet))
        else:
             print(_("debug_nothing_fit", snippet=block_snippet))

        if final_frame:
            if not took_duplicate:
                self._add_to_history(final_frame)
            
            return self._create_search_result(block, final_frame, final_score)
        
        return None
    
    def _process_segment_results(
        self, 
        block: ScenarioBlock, 
        segment_results: List[tuple[VideoSegment, float]], 
        block_snippet: str
    ) -> Optional[SearchResult]:
        """Обрабатывает результаты поиска сегментов"""
        absolute_best_segment, absolute_best_score = segment_results[0]
        print(_("debug_plan_b_candidate", snippet=block_snippet, filename=absolute_best_segment.video_filename, score=absolute_best_score))

        unique_segment = None
        unique_score = 0.0
        
        for segment, score in segment_results:
            if score < self.score_threshold:
                break 
            
            if not self._is_duplicate_segment(segment):
                unique_segment = segment
                unique_score = score
                print(_("debug_unique_found", snippet=block_snippet, score=score))
                break

        final_segment = None
        final_score = 0.0
        took_duplicate = False

        if unique_segment:
            final_segment = unique_segment
            final_score = unique_score
        elif absolute_best_score >= self.score_threshold:
            final_segment = absolute_best_segment
            final_score = absolute_best_score
            took_duplicate = True
            print(_("debug_taking_duplicate", snippet=block_snippet))
        else:
             print(_("debug_nothing_fit", snippet=block_snippet))

        if final_segment:
            if not took_duplicate:
                self._add_segment_to_history(final_segment)
            
            return self._create_search_result_from_segment(block, final_segment, final_score)
        
        return None
        
    def _is_duplicate(self, frame: VisualFrame) -> bool:
        """Проверяет, является ли кадр дубликатом"""
        for used_file, used_time in self.used_frames_history:
            if (frame.video_filename == used_file and 
                abs(frame.timestamp - used_time) < self.time_window):
                return True
        return False
    
    def _is_duplicate_segment(self, segment: VideoSegment) -> bool:
        """Проверяет, является ли сегмент дубликатом"""
        middle_time = segment.get_middle_timestamp()
        for used_file, used_time in self.used_frames_history:
            if (segment.video_filename == used_file and 
                abs(middle_time - used_time) < self.time_window):
                return True
        return False
    
    def _add_to_history(self, frame: VisualFrame) -> None:
        """Добавляет кадр в историю использованных"""
        self.used_frames_history.append((frame.video_filename, frame.timestamp))
        if len(self.used_frames_history) > self.history_size:
            self.used_frames_history.pop(0)
    
    def _add_segment_to_history(self, segment: VideoSegment) -> None:
        """Добавляет сегмент в историю использованных"""
        middle_time = segment.get_middle_timestamp()
        self.used_frames_history.append((segment.video_filename, middle_time))
        if len(self.used_frames_history) > self.history_size:
            self.used_frames_history.pop(0)
    
    def _create_search_result(
        self,
        block: ScenarioBlock,
        frame: VisualFrame,
        score: float
    ) -> SearchResult:
        """Создает объект результата поиска из кадра"""
        m = int(frame.timestamp // 60)
        s = int(frame.timestamp % 60)
        timecode = f"{m:02d}:{s:02d}"
        
        tags = self.search_engine.extract_tags(block.text)
        
        return SearchResult(
            scenario_text_snippet=block.text[:100] + "..." if len(block.text) > 100 else block.text,
            video_filename=frame.video_filename,
            timecode_str=timecode,
            timestamp_seconds=frame.timestamp,
            accuracy_score=score,
            frame_path=frame.frame_path,
            tags=tags
        )
    
    def _create_search_result_from_segment(
        self,
        block: ScenarioBlock,
        segment: VideoSegment,
        score: float
    ) -> SearchResult:
        """Создает объект результата поиска из сегмента"""
        middle_time = segment.get_middle_timestamp()
        m = int(middle_time // 60)
        s = int(middle_time % 60)
        timecode = f"{m:02d}:{s:02d}"
        
        tags = self.search_engine.extract_tags(block.text)
        
        return SearchResult(
            scenario_text_snippet=block.text[:100] + "..." if len(block.text) > 100 else block.text,
            video_filename=segment.video_filename,
            timecode_str=timecode,
            timestamp_seconds=middle_time,
            accuracy_score=score,
            frame_path=segment.preview_frame_path,
            tags=tags,
            start_time=segment.start_time,
            end_time=segment.end_time,
            segment_id=segment.segment_id
        )
    
    def _result_to_dict(self, result: SearchResult) -> dict:
        """Преобразует результат в словарь для GUI"""
        return {
            "text_snippet": result.scenario_text_snippet,
            "filename": result.video_filename,
            "tags": ", ".join(result.tags) if result.tags else "",
            "timecode": result.timecode_str,
            "accuracy": int(result.accuracy_score * 100),
            "timestamp": result.timestamp_seconds,
            "frame_path": result.frame_path,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "segment_id": result.segment_id,
            "is_segment": result.is_segment()
        }
    
    def record_feedback(self, frame_meta: dict, is_positive: bool) -> bool:
        """Записывает обратную связь"""
        try:
            if "segment_id" in frame_meta and frame_meta.get("segment_id"):
                from domain import VideoSegment
                segment = VideoSegment(
                    video_filename=frame_meta.get("filename", ""),
                    start_time=float(frame_meta.get("start_time", 0)),
                    end_time=float(frame_meta.get("end_time", 0)),
                    segment_id=frame_meta.get("segment_id", ""),
                    preview_frame_path=frame_meta.get("frame_path", ""),
                    key_frames=[]
                )
                self.search_engine.record_segment_feedback(segment, is_positive)
            else:
                frame = VisualFrame(
                    video_filename=frame_meta.get("filename", ""),
                    timestamp=float(frame_meta.get("timestamp", 0)),
                    frame_path=frame_meta.get("frame_path", "")
                )
                self.search_engine.record_feedback(frame, is_positive)
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(_("feedback_save_error", error=e))
            return False