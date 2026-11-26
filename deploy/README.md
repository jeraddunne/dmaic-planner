# Deploying the DMAIC Planner app to Google Cloud Run

The app runs from the `Dockerfile` at the repository root. Cloud Run builds that file
on Google's servers (`gcloud run deploy --source .`) and gives it a public HTTPS link.
Running and testing the app locally is covered in [`app/README.md`](../app/README.md).

Settings the scripts use: project `dmaic-planner-ari510`, service name `dmaic-planner`,
region `us-central1`, model `c2`, 1 CPU, 2 GiB memory, 0 to 2 instances, public (no
sign-in), session affinity on.

## One-time setup

Already done for `dmaic-planner-ari510` (project created, billing linked, the three
services enabled); kept here for anyone setting up their own project. Steps 2 to 4
happen in the browser.

1. Install the Google Cloud CLI and check it works: `gcloud --version`
2. Redeem the course coupon (from Lab 4). It creates a billing account that holds the credits.
3. In the [Cloud console](https://console.cloud.google.com/projectcreate), create a project
   and write down its **project ID** (not the name).
4. Link the project to the coupon's billing account: Billing > My projects > Change billing.
   Optional but sensible: Billing > Budgets & alerts > create a small budget with an email
   alert, so a mistake cannot quietly use the credits.
5. Sign in and point the CLI at the project:

   ```
   gcloud auth login
   gcloud config set project PROJECT_ID
   ```

6. Turn on the three services the deploy uses:

   ```
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

## Deploy

From the repository root, after `gcloud auth login`:

```powershell
# Windows PowerShell
.\deploy\cloudrun_deploy.ps1
```

```bash
# macOS, Linux, Cloud Shell
bash deploy/cloudrun_deploy.sh
```

The first deploy asks to create an Artifact Registry repository named
`cloud-run-source-deploy`; answer **Y**. The build takes several minutes the first
time (it installs CPU-only PyTorch and bakes the sentence encoder into the image).
The script ends by printing the public URL. Open it, click an example, then
**Recommend a route**.

Options: `-ProjectId` (default `dmaic-planner-ari510`), `-Region` (default
`us-central1`), `-Model`, `-MinInstances` (default 0), `-MaxInstances` (default 2),
`-Memory` (default `2Gi`), `-Cpu` (default 1). In the bash script:
`deploy/cloudrun_deploy.sh [PROJECT_ID] [REGION] [MODEL]`, and `MIN_INSTANCES=1`,
`MAX_INSTANCES`, `MEMORY`, `CPU` as environment variables.

Only these files are uploaded (`.gcloudignore` is an allowlist): `Dockerfile`,
`.dockerignore`, `app/`, `src/`, `rules/` and `models/phase3/c2/model.json`. The tests,
`docs/`, `data/` and any local virtual environment stay on your computer.

## Which model runs

The app loads whatever `DMAIC_MODEL` names. The deploy scripts default it to the
`DEFAULT_MODEL` line in `app/predictor.py` (now `c2`), so switching for good is one line
in that file, then deploy again. For a one-off deploy without changing the file:
`-Model placeholder` deploys the keyword-rules placeholder, which is useful only to check
a deployment without the model. See `app/README.md` for the accepted values.

## Availability window (Dec 8 to Dec 10)

The app must work from the start of presentations (Tue Dec 8, 1:30 PM EST) until at
least 48 hours after they end (Thu Dec 10, 4:00 PM EST).

With 0 minimum instances (the default) the app costs nothing while idle, but the first
visit after a quiet spell waits for a cold start while a container boots and loads the
model. To keep one instance warm during the live demo only:

```
# before 1:30 PM EST on Dec 8
gcloud run services update dmaic-planner --region us-central1 --min-instances 1
# after the presentations end
gcloud run services update dmaic-planner --region us-central1 --min-instances 0
```

This is a cost tradeoff, and your call: a warm instance is billed for its CPU and
memory the whole time it is up, even with no visitors (current rates at
<https://cloud.google.com/run/pricing>). A few hours during the presentations is
small against the course credits; the full 48 hours costs proportionally more.
Running the deploy script again resets the minimum to 0 unless you pass
`-MinInstances 1`.

After Dec 10, 4:00 PM EST you may shut it down:
`gcloud run services delete dmaic-planner --region us-central1`.

## If something goes wrong

- **Permission error during the build** naming the project's default compute service account (its name ends in
  `-compute` at `developer.gserviceaccount.com`): newer projects build with that account, and it needs the Cloud Run Builder role.
  Grant it, using the exact account from the error message, then deploy again:

  ```
  gcloud projects add-iam-policy-binding dmaic-planner-ari510 --member=serviceAccount:ACCOUNT_FROM_ERROR --role=roles/run.builder
  ```

- **The page loads but predictions fail, or the service restarts**: Cloud console >
  Cloud Run > dmaic-planner > Logs. A "memory limit exceeded" line means raising
  `-Memory` to `4Gi`.
- **An API call that worked once says the session was not found**: with two instances
  running, the two requests of the curl call (see `app/README.md`) reached different
  instances. Browsers and `gradio_client` keep the session-affinity cookie and are not
  affected. Retry, or deploy with `-MaxInstances 1`.
