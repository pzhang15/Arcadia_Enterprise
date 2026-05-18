from mirage.resource.disk import DiskResource
from mirage.resource.gdocs.prompt import PROMPT, WRITE_PROMPT


class FakeGDocsResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
