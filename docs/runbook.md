# Owner runbook: daily publish (Workflow B)

Short steps for the owner. The workflow is `.github/workflows/daily_publish.yml`. Only the `main` branch publishes. Nothing here puts a secret value in the repo.

## 1. One-time setup

1. Create the `youtube` environment: Settings, Environments, New environment. Add three environment secrets: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN`.
2. Set the environment's deployment branches to "Selected branches" and allow only `main`. The upload job uses this environment, so no other branch can read the YouTube secrets.
3. Create the `ledger` branch once, from a fresh clone (not a worktree):
   ```
   git switch --orphan ledger
   mkdir -p data/published
   touch data/published/.gitkeep
   git add data/published/.gitkeep
   git commit -m "Start the publish ledger"
   git push origin ledger
   ```
   Until this branch exists, the render job cannot check it out, so the run goes red. That is the safe result.
4. Turn on the rulesets after the ledger branch workflow has merged, not before. Otherwise the old claim job's pushes to `main` fail.
   - `main`: restrict deletions, block force pushes, require a pull request (0 approvals), require the status check `check`. Add no bypass list.
   - `ledger`: restrict deletions and block force pushes. Do not tick "restrict updates", because it would block the bot too.
5. Add the agent deny rules in the Claude Code settings (owner only). Deny `git push` to `main` and to `ledger`, `gh pr merge`, `gh run rerun`, and `gh workflow run daily-publish`.
6. Set failure emails: Settings, Notifications, Actions. Turn on the email for failed workflow runs, so a red daily run reaches you.
7. Set artifact and log retention to 30 days or less: Settings, Actions, General. The render artifact already keeps only 1 day in the workflow file.
8. Set the Google OAuth consent screen to "In production" (Publish app). In "Testing", refresh tokens expire after 7 days.

## 2. A daily run went red

Open the run, then the first job that failed. Find the job name and the last message it printed.

1. **pick** (inside the render job): the step stops with one of these messages.
   - "pick gave an unexpected script id" or "unexpected script hash": nothing was claimed. Check the script file in `queue/approved/`. The next day retries.
   - "queue empty: no approved script is due": nothing was claimed and nothing was published. Refill the queue (step 5). Safe to leave red.
   - "ledger folder missing": the `ledger` branch is missing or moved. Check step 1.3. Nothing was claimed.
   - "unconfirmed claim for ...": a claim is kept. Go to step 3.
2. **render**: the render failed before any claim. Nothing was claimed. Fix the cause in the log. The next day retries.
3. **claim**: nothing was claimed or sent. Messages:
   - "the ledger already holds a record for this script": check the ledger for that script before anything else.
   - "main no longer holds the approved script that was rendered": a script changed on `main` after the render. Nothing was sent.
   - "unexpected run id or attempt" or a push error: nothing was sent.
4. **upload**: the guards print "nothing sent" when they stop before the upload. Messages:
   - "the ledger holds no claim from this run and attempt, nothing sent".
   - "the script differs from the rendered version, nothing sent".
   - If the "Upload to YouTube" step never started, nothing reached YouTube. The claim is kept until you delete its record (step 3).
   - If the "Upload to YouTube" step started and failed, check the channel first (step 3).
5. **record**: prints "the upload outcome is unknown, claim kept: check the channel" when the upload did not report a result. Also "unexpected video id, claim kept" and "the ledger holds no claim from this run for this script". In each case the claim stays on the ledger. Go to step 3.

## 3. A claim is kept

A kept claim blocks the next pick. Every later run stops with "unconfirmed claim for ...".

1. Check the YouTube channel first. Look for the video of that script.
2. If the video is on the channel: on the `ledger` branch, open `data/published/<script_id>.json`. Set `youtube_video_id` to the 11-character id from the video URL, and set `published_at` to the upload time in UTC, format `YYYY-MM-DDTHH:MM:SSZ`. Commit and push to `ledger`.
3. If no video is on the channel: on the `ledger` branch, delete `data/published/<script_id>.json`. Commit and push to `ledger`. The script is picked again on the next run.
4. Never re-run failed jobs while a claim is kept. A re-run of the whole workflow counts as a new run attempt and can change what the guards see.
5. The one safe re-run: the upload job succeeded and only the record job failed (for example, a push race). Re-run only the record job. It fills in the video id from the earlier upload.
6. A record with a video id is never changed by the workflow. Do not edit one unless step 2 says so.
7. Delete only claim-only ledger records, never one that has a video id.

## 4. Token revoke and rotate

Use this when a token may have leaked, or the upload job fails with an authorisation error.

1. Revoke the app: myaccount.google.com, Third-party access. Remove the app there.
2. Reset the OAuth client secret in the Google Cloud console if the client secret may have leaked.
3. Make a new refresh token in the OAuth 2.0 Playground, using the same client. Delete the Playground redirect URI from the client afterwards.
4. In Settings, Environments, `youtube`: replace `YOUTUBE_REFRESH_TOKEN` (and `YOUTUBE_CLIENT_SECRET` if you reset it). Do not paste values into issues, logs or commits.

## 5. Refill the sources and the queue

The queue runs at 7 videos a week. The sources last about two weeks.

1. Every second weekend, add about 14 new `sources/*.yaml` files by pull request. Follow the content rules in PLAN.md section 4. You review the facts yourself.
2. Merge the refill before the Sunday run of the weekly-scripts workflow (Workflow A).
3. When the batch pull request body says "sources exhausted", or a daily run stops with "queue empty", refill first. A "queue empty" run publishes nothing, so it is safe to leave red until the refill lands.

## 6. `lock-resolve` is red on a pull request

The `lock-resolve` job in CI resolves the hashed render and generate locks. Red means pip cannot install a lock as written.

1. Open the job and read the last pip error. It names the package and the reason (a cap, a missing hash, an sdist-only dependency).
2. A Dependabot bump: do not merge. If another package caps the bumped one, close the PR with `@dependabot ignore this major version` and add a bare ignore in `.github/dependabot.yml`. If the bumped package pulls in a new dependency, either bump both together or ignore it.
3. A lock you edited by hand: regenerate the affected block with `pip download` and `pip hash`, never type a hash.
4. Nothing was published or claimed; the job only resolves. Leave the PR open until it is green.
