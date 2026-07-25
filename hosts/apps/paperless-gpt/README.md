# Paperless-GPT

The independent `paperless-gpt` project runs on Apps LXC 112 and publishes
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
