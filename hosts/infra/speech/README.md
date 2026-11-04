# Shared speech API

Speaches provides private, authenticated OpenAI-compatible speech-to-text on
Infra at `http://192.168.0.110:8092/v1/audio/transcriptions`. It receives uploads;
it has no source-account credentials or shared-media mount. Clients must not
send this operator key to browsers or store it in an Obsidian vault. Reference
Boards uses its restricted archive connection instead.

The pinned CPU image runs as UID 1000 with two CPU cores, a 4 GiB memory limit,
one inference worker, int8 inference, and a 60-second model unload timeout.
Infra has four shared cores and 8 GiB RAM. No inference runs on the Mac.
The model cache is durable appdata in `/srv/appdata/docker/speech/models`;
it can be downloaded again. The retained API key is in PVE `/root/.env` and
the scoped root-only `speech/runtime.env` used by the container deployment.

From a committed PVE checkout, run `bash hosts/infra/speech/deploy.sh <commit>`.
The installer refuses implicit key rotation. It validates Compose before
activation and retains isolated source releases. Bootstrap initializes the
same state and deploys the same Compose definition. Verify with guest
`python3 <release>/hosts/infra/speech/verify.py`; this tests health/auth without
inference. Check the end-to-end evidence for the model and measured extraction.

The service is API-only (interactive UI disabled), so it needs no Homarr tile.
Pulse must cover the container and shared monitoring probes `/health`. Image
updates are manual and pinned; model downloads require outbound HTTPS.

Rollback uses the preceding committed Compose release and retained key/cache.
For first deployment, stop only the `speaches` container to disable the API;
retain appdata and transcript results. Scheduled appdata backups cover durable
derivatives and credentials; originals remain under the separate media contract.

Upstream: [installation](https://speaches.ai/installation/),
[configuration](https://speaches.ai/configuration/), and
[source](https://github.com/speaches-ai/speaches).
