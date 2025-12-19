
import os
import json
import threading
import re
import numpy as np
import torch
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
from domain import ISearchEngine, IFrameRepository, VisualFrame, VideoSegment


class ClipSearchEngine(ISearchEngine):
    """CLIP-based frame search engine"""
    
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
        self.segments: List[VideoSegment] = []
        self.embeddings: Optional[torch.Tensor] = None
        self.segment_embeddings: Optional[torch.Tensor] = None
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
        """Lazy initialization: loads model on first use"""
        if self._initialized:
            return
        
        print("🧠 Loading Multilingual CLIP model...")
        self.model = SentenceTransformer(self.model_name)
        self.frames = self.repository.load_all()
        self.segments = self.repository.load_all_segments()
        self._load_feedback()
        self._load_or_index_images()
        self._load_or_index_segments()
        self._initialized = True
    
    def is_ready(self) -> bool:
        """Checks if search engine is ready"""
        if not self._initialized:
            self._initialize()
        
        has_frames = self.embeddings is not None and len(self.frames) > 0
        has_segments = self.segment_embeddings is not None and len(self.segments) > 0
        return has_frames or has_segments
    
    def search(self, query_text: str, limit: int = 5) -> List[Tuple[VisualFrame, float]]:
        """Searches frames by text query"""
        if not self.is_ready():
            return []
        
        aggregated_hits = {}
        query_text = query_text.strip()
        
        tag_query = self._extract_tags_internal(query_text)
        
        
        if query_text:
            text_emb = self.model.encode(query_text, convert_to_tensor=True)
            text_hits = util.semantic_search(
                text_emb, self.embeddings, top_k=max(limit * 3, 15)
            )
            self._merge_hits(text_hits, "text", aggregated_hits)
        
        
        if tag_query:
            tag_emb = self.model.encode(tag_query, convert_to_tensor=True)
            tag_hits = util.semantic_search(
                tag_emb, self.embeddings, top_k=max(limit * 2, 10)
            )
            self._merge_hits(tag_hits, "tags", aggregated_hits)
        
        
        results = []
        for data in aggregated_hits.values():
            scores = data["scores"]
            combined = sum(
                self._weights.get(source, 0.0) * score 
                for source, score in scores.items()
            )
            if "text" not in scores:
                combined *= 0.8  
            results.append((data["frame"], combined))
        
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
        """Saves feedback"""
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
        """Extracts keywords from text (public interface method)"""
        tags_str = self._extract_tags_internal(text)
        return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    def _extract_tags_internal(self, text: str) -> str:
        """Extracts keywords from text"""
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
        """Encodes text into embedding"""
        return self.model.encode(text, convert_to_tensor=True)
    
    def _merge_hits(self, hits, source_label: str, storage: dict) -> None:
        """Merges search results"""
        for hit in hits[0]:
            idx = hit["corpus_id"]
            entry = storage.setdefault(idx, {"scores": {}, "frame": self.frames[idx]})
            score = float(hit["score"])
            entry["scores"][source_label] = max(entry["scores"].get(source_label, 0.0), score)
    
    def _feedback_key(self, frame: VisualFrame) -> str:
        """Generates feedback key"""
        ts = round(frame.timestamp, 2)
        return f"{frame.video_filename}|{ts}"
    
    def _load_feedback(self) -> None:
        """Loads feedback from file"""
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
        """Saves feedback to file"""
        os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
        data = {
            "positive": sorted(self.feedback["positive"]),
            "negative": sorted(self.feedback["negative"]),
        }
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_or_index_images(self) -> None:
        """Loads or creates frame embeddings"""
        if not self.frames:
            return
        
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
        """Performs full frame indexing"""
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
    
    def search_segments(self, query_text: str, limit: int = 5) -> List[Tuple[VideoSegment, float]]:
        """Searches segments by text query with averaging of key_frames embeddings"""
        if not self.is_ready() or not self.segments or self.segment_embeddings is None:
            return []
        
        aggregated_hits = {}
        query_text = query_text.strip()
        
        tag_query = self._extract_tags_internal(query_text)
        
        if query_text:
            text_emb = self.model.encode(query_text, convert_to_tensor=True)
            text_hits = util.semantic_search(
                text_emb, self.segment_embeddings, top_k=max(limit * 3, 15)
            )
            self._merge_segment_hits(text_hits, "text", aggregated_hits)
        
        if tag_query:
            tag_emb = self.model.encode(tag_query, convert_to_tensor=True)
            tag_hits = util.semantic_search(
                tag_emb, self.segment_embeddings, top_k=max(limit * 2, 10)
            )
            self._merge_segment_hits(tag_hits, "tags", aggregated_hits)
        
        results = []
        for data in aggregated_hits.values():
            scores = data["scores"]
            combined = sum(
                self._weights.get(source, 0.0) * score 
                for source, score in scores.items()
            )
            if "text" not in scores:
                combined *= 0.8
            results.append((data["segment"], combined))
        
        adjusted = []
        for segment, score in results:
            if segment.key_frames:
                key = self._feedback_key(segment.key_frames[0])
                if key in self.feedback["negative"]:
                    score *= 0.2
                elif key in self.feedback["positive"]:
                    score *= 1.25
            
            final_score = max(0.0, min(score, 1.0))
            adjusted.append((segment, final_score))
        
        adjusted.sort(key=lambda item: item[1], reverse=True)
        return adjusted[:limit]
    
    def _merge_segment_hits(self, hits, source_label: str, storage: dict) -> None:
        """Merges segment search results"""
        for hit in hits[0]:
            idx = hit["corpus_id"]
            entry = storage.setdefault(idx, {"scores": {}, "segment": self.segments[idx]})
            score = float(hit["score"])
            entry["scores"][source_label] = max(entry["scores"].get(source_label, 0.0), score)
    
    def record_segment_feedback(self, segment: VideoSegment, is_positive: bool) -> None:
        """Saves feedback for segment"""
        if segment is None or not segment.key_frames:
            return
        
        self.record_feedback(segment.key_frames[0], is_positive)
    
    def _load_or_index_segments(self) -> None:
        """Loads or creates segment embeddings"""
        if not self.segments:
            return
        
        segments_cache_file = self.cache_file.replace(".npy", "_segments.npy")
        
        if os.path.exists(segments_cache_file) and len(self.segments) > 0:
            try:
                cached_emb = np.load(segments_cache_file)
                if len(cached_emb) == len(self.segments):
                    self.segment_embeddings = torch.from_numpy(cached_emb)
                    print(f"⚡️ Кэш векторов сегментов загружен ({len(self.segment_embeddings)} шт).")
                    return
                else:
                    os.remove(segments_cache_file)
            except Exception:
                pass
        
        self._run_segment_indexing(segments_cache_file)
    
    def _run_segment_indexing(self, cache_file: str) -> None:
        """Performs full segment indexing with averaging of key_frames embeddings"""
        print(f"📊 Индексирую {len(self.segments)} сегментов...")
        
        segment_embeddings_list = []
        valid_segments = []
        
        for segment in self.segments:
            key_frame_paths = []
            for frame in segment.key_frames:
                if os.path.exists(frame.frame_path):
                    key_frame_paths.append(frame.frame_path)
            
            if not key_frame_paths:
                continue
            
            frame_embeddings = self.model.encode(
                key_frame_paths,
                batch_size=32,
                convert_to_tensor=True,
                show_progress_bar=False
            )
            
            if len(frame_embeddings.shape) == 1:
                segment_emb = frame_embeddings
            else:
                segment_emb = torch.mean(frame_embeddings, dim=0)
            
            segment_embeddings_list.append(segment_emb.cpu().numpy())
            valid_segments.append(segment)
        
        if segment_embeddings_list:
            self.segments = valid_segments
            self.segment_embeddings = torch.from_numpy(np.array(segment_embeddings_list))
            np.save(cache_file, self.segment_embeddings.cpu().numpy())
            print(f"✅ Индексация сегментов завершена и сохранена в кэш ({len(self.segments)} шт).")
        else:
            print("❌ Ошибка: Нет валидных сегментов для индексации.")

