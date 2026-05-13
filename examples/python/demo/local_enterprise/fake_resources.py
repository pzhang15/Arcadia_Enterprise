from mirage.resource.disk import DiskResource
from mirage.resource.gdocs.prompt import PROMPT as GDOCS_PROMPT
from mirage.resource.gdocs.prompt import WRITE_PROMPT as GDOCS_WRITE_PROMPT
from mirage.resource.gsheets.prompt import PROMPT as GSHEETS_PROMPT
from mirage.resource.gsheets.prompt import WRITE_PROMPT as GSHEETS_WRITE_PROMPT
from mirage.resource.slack.prompt import PROMPT as SLACK_PROMPT
from mirage.resource.slack.prompt import WRITE_PROMPT as SLACK_WRITE_PROMPT


class FakeSlackResource(DiskResource):
    PROMPT = SLACK_PROMPT
    WRITE_PROMPT = SLACK_WRITE_PROMPT


class FakeGSheetsResource(DiskResource):
    PROMPT = GSHEETS_PROMPT
    WRITE_PROMPT = GSHEETS_WRITE_PROMPT


class FakeGDocsResource(DiskResource):
    PROMPT = GDOCS_PROMPT
    WRITE_PROMPT = GDOCS_WRITE_PROMPT
