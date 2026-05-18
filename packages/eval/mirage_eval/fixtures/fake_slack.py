from mirage.resource.disk import DiskResource
from mirage.resource.slack.prompt import PROMPT, WRITE_PROMPT


class FakeSlackResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
