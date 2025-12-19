"""Google Docs client"""
from typing import Iterator, Optional
from googleapiclient.discovery import build
from domain import IDocumentSource, IAuthService, ScenarioBlock

from infrastructure.localization import _

class GoogleDocsClient(IDocumentSource):
    """Extracts data from Google Docs"""
    
    IGNORED_KEYWORDS = [
        "Рыба", "Контрасты", "Ссылка", "Insert", "Тизер", 
        "http", "Стендап", "Закадр", "Глава", "Теги от редактора"
    ]
    
    def __init__(self, auth_service: IAuthService):
        self.auth_service = auth_service
        self.doc_id: Optional[str] = None
        self.docs_service = None
        self._connected = False
    
    def connect(self, resource_id: str) -> None:
        """Connects to document"""
        if not self.auth_service.is_authenticated():
            if not self.auth_service.authenticate():
                raise ConnectionError(_("google_auth_failed"))
        
        self.doc_id = resource_id
        credentials = self.auth_service.get_credentials()
        if not credentials:
            raise ConnectionError(_("google_no_credentials"))
        
        self.docs_service = build('docs', 'v1', credentials=credentials)
        self._connected = True
    
    def is_connected(self) -> bool:
        """Checks connection"""
        return self._connected and self.docs_service is not None
        
    def extract_blocks(self) -> Iterator[ScenarioBlock]:
        """Extracts text blocks from document"""
        if not self.is_connected():
            raise ConnectionError(_("google_not_connected_to_doc"))
        
        try:
            document = self.docs_service.documents().get(documentId=self.doc_id).execute()
            body_content = document.get('body', {}).get('content', [])
        except Exception as e:
            raise ConnectionError(_("google_doc_read_error", error=e))
        
        block_counter = 0
        for element in body_content:
            if 'table' in element:
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_text = self._extract_text_from_cell(cell)
                        if self._is_valid_block(cell_text):
                            block_counter += 1
                            yield ScenarioBlock(
                                text=cell_text,
                                block_id=f"table_cell_{block_counter}"
                            )
            
            elif 'paragraph' in element:
                paragraph_text = self._extract_text_from_paragraph(element['paragraph'])
                if self._is_valid_block(paragraph_text):
                    block_counter += 1
                    yield ScenarioBlock(
                        text=paragraph_text,
                        block_id=f"paragraph_{block_counter}"
                    )
    
    def _extract_text_from_paragraph(self, paragraph_structure: dict) -> str:
        """Extracts text from paragraph structure"""
        text_parts = []
        for element in paragraph_structure.get('elements', []):
            if 'textRun' in element:
                text_parts.append(element['textRun'].get('content', ''))
        return "".join(text_parts).strip()
    
    def _extract_text_from_cell(self, cell_data: dict) -> str:
        """Extracts text from table cell"""
        full_text = []
        for content_item in cell_data.get('content', []):
            if 'paragraph' in content_item:
                text = self._extract_text_from_paragraph(content_item['paragraph'])
                if text:
                    full_text.append(text)
        return "\n".join(full_text).strip()
    
    def _is_valid_block(self, text: str) -> bool:
        """Checks if text is a valid block"""
        if len(text) < 20:
            return False
        
        text_lower = text.lower()
        for keyword in self.IGNORED_KEYWORDS:
            if keyword.lower() in text_lower:
                return False
        
        return True