"""Application Service: Анализ документа и поиск кадров"""
from typing import List, Optional, Callable
from domain.interfaces import IDocumentSource, ISearchEngine, ILogger
from domain.entities import ScenarioBlock, VisualFrame, SearchResult
import traceback


from infrastructure.localization import _

class DocumentAnalysisService:
    """Single Responsibility: Координация анализа документа и поиска кадров"""
    
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
            # Используем локализованное сообщение об ошибке
            raise RuntimeError(_("search_engine_not_ready"))
        
        results = []
        blocks = list(self.document_source.extract_blocks())
        total_blocks = len(blocks)
        
        if progress_callback:
            # Локализованный статус для GUI
            progress_callback("status", _("analysis_blocks_found", count=total_blocks))
        
        # Локализованный дебаг-принт
        print(_("debug_start_processing_blocks", count=total_blocks))

        for idx, block in enumerate(blocks, 1):
            # Локализованный дебаг-принт с параметрами
            print(_("debug_block_start", idx=idx, snippet=block.text[:20]))

            if progress_callback:
                # Локализованный статус прогресса для GUI
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
                
                # Локализованный дебаг-принт успеха
                print(_("debug_block_success", idx=idx))

            except Exception as e:
                # Локализованный вывод ошибки в консоль
                print(_("error_critical_on_block", idx=idx))
                print(_("error_message_label", error=e))
                print(_("error_traceback_start"))
                traceback.print_exc()
                print(_("error_traceback_end"))

        # Локализованный дебаг-принт завершения
        print(_("debug_processing_finished"))

        if progress_callback:
            # Надсилаємо сигнал "finished". Дані не важливі, передаємо None.
            progress_callback("finished", None)
        
        return results

    def _process_block(self, block: ScenarioBlock) -> Optional[SearchResult]:
        """Обрабатывает один блок сценария (Стратегія: Унікальний > Дублікат > Нічого)"""
        block_snippet = block.text[:20] + "..."
        # Используем _() для локализации дебаг-сообщений
        print(_("debug_process_block_start", snippet=block_snippet))
        
        # Отримуємо кандидатів
        search_results = self.search_engine.search(block.text, limit=12)
        
        if not search_results:
             print(_("debug_neural_found_nothing", snippet=block_snippet))
             return None

        # Запам'ятовуємо найкращий кадр (навіть якщо він дублікат) - це наш "план Б"
        absolute_best_frame, absolute_best_score = search_results[0]
        print(_("debug_plan_b_candidate", snippet=block_snippet, filename=absolute_best_frame.video_filename, score=absolute_best_score))

        # Спроба знайти УНІКАЛЬНИЙ кадр (План А)
        unique_frame = None
        unique_score = 0.0
        
        for frame, score in search_results:
            # Якщо навіть найкращі кадри вже мають поганий скор, далі шукати немає сенсу
            if score < self.score_threshold:
                break 
            
            # Якщо це НЕ дублікат - ура, ми знайшли!
            if not self._is_duplicate(frame):
                unique_frame = frame
                unique_score = score
                print(_("debug_unique_found", snippet=block_snippet, score=score))
                break # Знайшли план А, виходимо

        # Фінальний вибір
        final_frame = None
        final_score = 0.0
        took_duplicate = False

        if unique_frame:
            # Спрацював План А
            final_frame = unique_frame
            final_score = unique_score
        elif absolute_best_score >= self.score_threshold:
            # План А провалився. Застосовуємо План Б (беремо дублікат), якщо його скор нормальний.
            final_frame = absolute_best_frame
            final_score = absolute_best_score
            took_duplicate = True
            print(_("debug_taking_duplicate", snippet=block_snippet))
        else:
             print(_("debug_nothing_fit", snippet=block_snippet))

        # Якщо ми щось вибрали
        if final_frame:
            # ВАЖЛИВО: Додаємо в історію ТІЛЬКИ якщо це був УНІКАЛЬНИЙ кадр.
            if not took_duplicate:
                self._add_to_history(final_frame)
            
            return self._create_search_result(block, final_frame, final_score)
        
        return None
        
    def _is_duplicate(self, frame: VisualFrame) -> bool:
        """Проверяет, является ли кадр дубликатом"""
        for used_file, used_time in self.used_frames_history:
            if (frame.video_filename == used_file and 
                abs(frame.timestamp - used_time) < self.time_window):
                return True
        return False
    
    def _add_to_history(self, frame: VisualFrame) -> None:
        """Добавляет кадр в историю использованных"""
        self.used_frames_history.append((frame.video_filename, frame.timestamp))
        if len(self.used_frames_history) > self.history_size:
            self.used_frames_history.pop(0)
    
    def _create_search_result(
        self,
        block: ScenarioBlock,
        frame: VisualFrame,
        score: float
    ) -> SearchResult:
        """Создает объект результата поиска"""
        m = int(frame.timestamp // 60)
        s = int(frame.timestamp % 60)
        timecode = f"{m:02d}:{s:02d}"
        
        # Извлекаем теги через интерфейс
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
    
    def _result_to_dict(self, result: SearchResult) -> dict:
        """Преобразует результат в словарь для GUI"""
        return {
            "text_snippet": result.scenario_text_snippet,
            "filename": result.video_filename,
            "tags": ", ".join(result.tags) if result.tags else "",
            "timecode": result.timecode_str,
            "accuracy": int(result.accuracy_score * 100),
            "timestamp": result.timestamp_seconds,
            "frame_path": result.frame_path
        }
    
    def record_feedback(self, frame_meta: dict, is_positive: bool) -> bool:
        """Записывает обратную связь"""
        try:
            frame = VisualFrame(
                video_filename=frame_meta.get("filename", ""),
                timestamp=float(frame_meta.get("timestamp", 0)),
                frame_path=frame_meta.get("frame_path", "")
            )
            self.search_engine.record_feedback(frame, is_positive)
            return True
        except Exception as e:
            if self.logger:
                # Локализация сообщения в логгере
                self.logger.warning(_("feedback_save_error", error=e))
            return False