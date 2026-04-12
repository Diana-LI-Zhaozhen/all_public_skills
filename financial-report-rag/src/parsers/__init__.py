from .pdf_parser import PDFParser
from .html_parser import HTMLParser
from .xml_parser import XMLParser
from .txt_parser import TXTParser
from .xsd_parser import XSDParser
from .xlsx_parser import XLSXParser
from .json_parser import JSONParser
from .dispatcher import FileDispatcher

__all__ = [
    "PDFParser",
    "HTMLParser",
    "XMLParser",
    "TXTParser",
    "XSDParser",
    "XLSXParser",
    "JSONParser",
    "FileDispatcher",
]
