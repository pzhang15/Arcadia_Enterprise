from mirage.resource.disk import DiskResource
from mirage.resource.gsheets.prompt import PROMPT, WRITE_PROMPT


class FakeGSheetsResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
