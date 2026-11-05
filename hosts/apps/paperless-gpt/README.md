# Paperless-GPT

Paperless-GPT is **optional and disabled by default**. Rafael is not using it;
an absent OpenAI key is expected and does not block bootstrap.
`PAPERLESS_GPT_ENABLED=false` skips preparation/deployment and requires no
running container, active proxy route, or Homarr tile. Paperless-ngx remains
active. The local Paperless API token is still retained for its health verifier.

When explicitly enabled, the independent `paperless-gpt` project runs on Apps
LXC 112 and publishes
`192.168.0.112:8003`. It reaches Paperless-ngx as
`http://paperless-ngx:8000` over the externally prepared
`dothomelab-paperless` Docker bridge; this avoids a cross-project
`depends_on` contract while bootstrap preserves deployment order.

NPM publishes `https://paperless-gpt.rafael.media` only to LAN
`192.168.0.0/24` and Tailscale `100.64.0.0/10`. Keep it private: upstream
provides no native authentication, and anyone who reaches it can alter
Paperless documents, change settings, and spend LLM credits.

Persistent prompts, configuration, and SQLite state are under
`/srv/appdata/docker/paperless/gpt`. The production `/root/.env` stores the
fixed 40-hex Django REST Framework token and OpenAI API key. The bootstrap
token reconciler creates a dedicated password-disabled Paperless superuser,
binds the declared token through Django's ORM, and then restarts only
Paperless-GPT.

Paperless-GPT uses OpenAI only. `PDF_UPLOAD` and `PDF_REPLACE` remain disabled;
do not enable document replacement until a current logical dump and isolated
restore test have passed and original documents have separate verified
protection. Changing providers or the upload/replacement policy requires an
explicit Compose and recovery-contract change.

## Enable or disable

To enable, supply a real `PAPERLESS_GPT_OPENAI_API_KEY` in PVE `/root/.env`
and set `PAPERLESS_GPT_ENABLED=true`. Run its prepare script, quiet Compose
validation and deployment, then the API-token configurator and verifier with
the dotenv loader. Reconcile NPM routes and Homarr with the same flag exported.
Bootstrap performs this sequence on rebuild. Never use a dummy external key.

The flag does not delete data or stop an already running container. To disable
an active installation, stop its container deliberately, set the flag false,
and reconcile the routes/tiles; preserve `/srv/appdata/docker/paperless/gpt`
and the retained image for rollback. The verifier fails if a disabled service
is still running. For route/dashboard-only commands, export the flag explicitly
when enabled; their default is disabled. No provider credentials are needed by
those commands.
