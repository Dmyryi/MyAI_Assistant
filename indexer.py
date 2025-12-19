"""
Video indexing - uses new architecture
"""
from infrastructure.persistence import VisualFrameRepository
from infrastructure.ai import VideoIndexer
from application.video_indexing_service import VideoIndexingService


def run_indexing():
    """Main function for launching visual indexing"""
    print("🔄 ЗАПУСК ВИЗУАЛЬНОГО ИНДЕКСАТОРА...")
    
    repository = VisualFrameRepository()
    indexer = VideoIndexer()
    service = VideoIndexingService(indexer, repository)
    
    success_count = service.index_new_videos()
    
    if success_count > 0:
        print(f"✅ Успешно проиндексировано видео: {success_count}")
    else:
        print("🎉 Индекс актуален. Новых видео для индексации нет.")


if __name__ == "__main__":
    run_indexing()
