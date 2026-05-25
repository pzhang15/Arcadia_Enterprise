from mirage.resource.disk import DiskResource

PROMPT = """\
{prefix}
  repos/<org>/<repo>/
    deployments/<deploy-id>.json
    commits/<short-sha>.json
    pulls/<number>.json

  Deployment JSON: id, environment, ref, sha, creator, created_at, statuses[].
  Commit JSON: sha, commit.author, commit.message, files[].filename, files[].patch.
  Pull request JSON: number, title, user.login, state, merged, head, base, body.

  Listing helpers:
    ls   {prefix}/repos/northhill/platform-api/deployments/
    cat  {prefix}/repos/northhill/platform-api/commits/f3a1b2c8.json
    jq  '.commit.message' {prefix}/repos/northhill/platform-api/commits/*.json"""

WRITE_PROMPT = ""


class FakeGitHubResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
