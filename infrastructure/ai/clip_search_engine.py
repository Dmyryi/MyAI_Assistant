"""Dependency Inversion: Реализация поискового движка на CLIP"""
import os
import json
import threading
import re
import numpy as np
import torch
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
from domain.interfaces import ISearchEngine, IFrameRepository
from domain.entities import VisualFrame


class ClipSearchEngine(ISearchEngine):
    """Single Responsibility: Поиск кадров по тексту с помощью CLIP"""
    
    def __init__(
        self, 
        repository: IFrameRepository,
        model_name: str = 'clip-ViT-B-32-multilingual-v1',
        cache_file: str = "data/visual_db.npy",
        feedback_file: str = "data/feedback.json"
    ):
        self.repository = repository
        self.model_name = model_name
        self.cache_file = cache_file
        self.feedback_file = feedback_file
        self.model: Optional[SentenceTransformer] = None
        self.frames: List[VisualFrame] = []
        self.embeddings: Optional[torch.Tensor] = None
        self.feedback_lock = threading.Lock()
        self.feedback = {"positive": set(), "negative": set()}
        self._weights = {"text": 0.7, "tags": 0.3}
        self._stop_words = {
            "и", "в", "на", "с", "по", "к", "о", "за", "для", "как", "что", "это", "из", "или", "но",
            "the", "and", "for", "with", "about", "from", "into", "over", "under", "been", "were",
            "was", "are", "you", "your", "our", "мы", "они", "она", "он", "его", "ее", "их", "там",
            "then", "than", "that", "this", "those", "these", "потом", "тогда", "еще", "ещё",
        }
        self._initialized = False
    
    def _initialize(self) -> None:
        """Lazy initialization: загружает модель только при первом использовании"""
        if self._initialized:
            return
        
        print("🧠 Загружаю Международную Нейросеть (Multilingual CLIP)...")
        self.model = SentenceTransformer(self.model_name)
        self.frames = self.repository.load_all()
        self._load_feedback()
        self._load_or_index_images()
        self._initialized = True
    
    def is_ready(self) -> bool:
        """Проверяет готовность движка"""
        if not self._initialized:
            self._initialize()
        return self.embeddings is not None and len(self.frames) > 0
    
    def search(self, query_text: str, limit: int = 5) -> List[Tuple[VisualFrame, float]]:
        """Ищет кадры по текстовому запросу"""
        if not self.is_ready():
            return []
        
        aggregated_hits = {}
        query_text = query_text.strip()
        
        tag_query = self._extract_tags_internal(query_text)
        
        # Поиск по полному тексту
        if query_text:
            text_emb = self.model.encode(query_text, convert_to_tensor=True)
            text_hits = util.semantic_search(
                text_emb, self.embeddings, top_k=max(limit * 3, 15)
            )
            self._merge_hits(text_hits, "text", aggregated_hits)
        
        # Поиск по тегам
        if tag_query:
            tag_emb = self.model.encode(tag_query, convert_to_tensor=True)
            tag_hits = util.semantic_search(
                tag_emb, self.embeddings, top_k=max(limit * 2, 10)
            )
            self._merge_hits(tag_hits, "tags", aggregated_hits)
        
        # Объединение результатов
        results = []
        for data in aggregated_hits.values():
            scores = data["scores"]
            combined = sum(
                self._weights.get(source, 0.0) * score 
                for source, score in scores.items()
            )
            if "text" not in scores:
                combined *= 0.8  # Штраф за отсутствие текстового совпадения
            results.append((data["frame"], combined))
        
        # Применение обратной связи
        adjusted = []
        for frame, score in results:
            key = self._feedback_key(frame)
            if key in self.feedback["negative"]:
                score *= 0.2
            elif key in self.feedback["positive"]:
                score *= 1.25


            final_score = max(0.0, min(score, 1.0))


            adjusted.append((frame, final_score))
        
        adjusted.sort(key=lambda item: item[1], reverse=True)
        return adjusted[:limit]
    
    def record_feedback(self, frame: VisualFrame, is_positive: bool) -> None:
        """Сохраняет обратную связь"""
        if frame is None:
            return
        
        key = self._feedback_key(frame)
        with self.feedback_lock:
            if is_positive:
                self.feedback["negative"].discard(key)
                self.feedback["positive"].add(key)
            else:
                self.feedback["positive"].discard(key)
                self.feedback["negative"].add(key)
            self._persist_feedback()
    
    def extract_tags(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста (публичный метод интерфейса)"""
        tags_str = self._extract_tags_internal(text)
        return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    def _extract_tags_internal(self, text: str) -> str:
        """Извлекает ключевые слова из текста"""
        tokens = re.findall(r"[A-Za-zА-Яа-яёЁ0-9]+", text.lower())
        keywords = []
        seen = set()
        
        for token in tokens:
            if len(token) < 4 or token in self._stop_words:
                continue
            if token not in seen:
                seen.add(token)
                keywords.append(token)
            if len(keywords) >= 12:
                break
        
        # Биграммы
        bigrams = []
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            if a in self._stop_words or b in self._stop_words:
                continue
            phrase = f"{a} {b}"
            if len(phrase) >= 8:
                bigrams.append(phrase)
            if len(bigrams) >= 4:
                break
        
        combined = keywords + bigrams
        return ", ".join(combined[:15])
    
    def _encode_text(self, text: str) -> torch.Tensor:
        """Кодирует текст в эмбеддинг"""
        return self.model.encode(text, convert_to_tensor=True)
    
    def _merge_hits(self, hits, source_label: str, storage: dict) -> None:
        """Объединяет результаты поиска"""
        for hit in hits[0]:
            idx = hit["corpus_id"]
            entry = storage.setdefault(idx, {"scores": {}, "frame": self.frames[idx]})
            score = float(hit["score"])
            entry["scores"][source_label] = max(entry["scores"].get(source_label, 0.0), score)
    
    def _feedback_key(self, frame: VisualFrame) -> str:
        """Генерирует ключ для обратной связи"""
        ts = round(frame.timestamp, 2)
        return f"{frame.video_filename}|{ts}"
    
    def _load_feedback(self) -> None:
        """Загружает обратную связь из файла"""
        if not os.path.exists(self.feedback_file):
            return
        
        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.feedback["positive"] = set(data.get("positive", []))
            self.feedback["negative"] = set(data.get("negative", []))
        except Exception:
            pass
    
    def _persist_feedback(self) -> None:
        """Сохраняет обратную связь в файл"""
        os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
        data = {
            "positive": sorted(self.feedback["positive"]),
            "negative": sorted(self.feedback["negative"]),
        }
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_or_index_images(self) -> None:
        """Загружает или создает эмбеддинги кадров"""
        if not self.frames:
            return
        
        # Проверка кэша
        if os.path.exists(self.cache_file) and len(self.frames) > 0:
            try:
                cached_emb = np.load(self.cache_file)
                if len(cached_emb) == len(self.frames):
                    self.embeddings = torch.from_numpy(cached_emb)
                    print(f"⚡️ Кэш векторов загружен ({len(self.embeddings)} шт).")
                    return
                else:
                    os.remove(self.cache_file)
            except Exception:
                pass
        
        self._run_full_indexing()
    
    def _run_full_indexing(self) -> None:
        """Выполняет полную индексацию кадров"""
        print(f"📊 Индексирую {len(self.frames)} ключевых кадров...")
        image_paths = []
        valid_frames = []
        
        for frame in self.frames:
            if os.path.exists(frame.frame_path):
                image_paths.append(frame.frame_path)
                valid_frames.append(frame)
        
        self.frames = valid_frames
        if image_paths:
            print(f"🚀 Начинаю обработку {len(image_paths)} файлов...")
            self.embeddings = self.model.encode(
                image_paths, 
                batch_size=32, 
                convert_to_tensor=True, 
                show_progress_bar=True
            )
            np.save(self.cache_file, self.embeddings.cpu().numpy())
            print("✅ Индексация завершена и сохранена в кэш.")
        else:
            print("❌ Ошибка: Нет файлов для индексации.")

