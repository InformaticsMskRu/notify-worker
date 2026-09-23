# Deploying notify-worker on a new node

notify-worker reads ejudge run notifications from a Redis stream and forwards
them to rmatics over HTTP. It has no database and keeps no local state, so it
only needs two things over the network:

- the **Redis instance that ejudge writes `ejudge.notify` to**;
- the rmatics endpoint in `RMATICS_ALIVE_URL`.

Each notification is sent with this judge's ejudge API token
(`EJUDGE_API_TOKEN`), which rmatics checks against its `judges.json`.

The container uses the host's network (`network_mode: host`), so addresses
in `.env` resolve exactly as they do on the node itself.

All commands below assume the repo lives in `/opt/notify-worker`.

## 1. Prerequisites

Install git, Docker Engine and the Docker Compose plugin, then check them:

```bash
git --version
docker compose version
docker info
```

**Don't use the snap package.** If `which docker` prints `/snap/bin/docker`,
Docker is sandboxed and can't read `/opt`, and every compose command fails
with `no configuration file provided: not found`. Remove it
(`sudo snap remove --purge docker`) and install Docker Engine with the Compose
plugin from Docker's apt repository
(https://docs.docker.com/engine/install/ubuntu/), then enable it at boot:

```bash
sudo systemctl enable --now docker
```

If `docker info` fails with a permission error, add your user to the `docker`
group (`sudo usermod -aG docker $USER`) and log in again.

## 2. Check out the code

```bash
sudo mkdir -p /opt/notify-worker
sudo chown $USER: /opt/notify-worker
git clone https://github.com/InformaticsMskRu/notify-worker.git /opt/notify-worker
cd /opt/notify-worker/deploy
```

To deploy a branch other than `master`, add `--branch <name>` to `git clone`.

All remaining commands are run from `/opt/notify-worker/deploy`.

## 3. Create `.env`

```bash
cp .env.example .env
chmod 600 .env
```

Fill it in:

| Variable | Required | Notes |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | yes | e.g. `notify-worker`. If empty, compose names the project `deploy`. |
| `REDIS_HOST`, `REDIS_PORT` | yes | Redis that ejudge publishes to. If it runs on this node, `127.0.0.1` works. |
| `REDIS_USER`, `REDIS_PASSWORD` | if Redis has auth | Pasted into a URL as is: **URL-encode** `@ : / # ? %` and spaces (e.g. `p@ss` → `p%40ss`). |
| `JUDGE_ID` | yes | Numeric id of this ejudge instance in rmatics' `judges.json`. |
| `EJUDGE_API_TOKEN` | yes | This judge's ejudge API token, the same one as in `judges.json` for `JUDGE_ID`. |
| `RMATICS_ALIVE_URL` | yes | `https://informatics.msk.ru/py/problem/run/action/update_from_ejudge_v2` (see below). |
| `LOG_LEVEL` | no | Default `INFO`. |

`.env` is ignored by git and excluded from the Docker image, so the secrets
stay on this node.

**`RMATICS_ALIVE_URL`.** The public URL goes through the pynformatics proxy
(InformaticsMskRu/informatics-mccme-ru#296), which forwards the request to
rmatics' `update_from_ejudge_v2`. Until that proxy is deployed, use the
internal rmatics address instead, if this node can reach it:
`http://<rmatics-host>:12345/problem/run/action/update_from_ejudge_v2`.

## 4. Build the image

```bash
docker compose build --pull
```

## 5. Check connectivity from the container

These commands run inside the image, so they use the same network and DNS as
the worker.

Redis:

```bash
docker compose run --rm --no-deps notify-worker python -c "import os, redis; r = redis.from_url(os.environ['REDIS_URL'], socket_connect_timeout=5); print('ping:', r.ping())"
```

rmatics (TCP connect only, nothing is sent):

```bash
docker compose run --rm --no-deps notify-worker python -c "import os, socket; from urllib.parse import urlsplit; u = urlsplit(os.environ['RMATICS_ALIVE_URL']); p = u.port or (443 if u.scheme == 'https' else 80); socket.create_connection((u.hostname, p), timeout=5); print('rmatics reachable:', u.hostname, p)"
```

Fix any failure before continuing. Typical causes are a firewall, a Redis
that listens only on another interface, or an unencoded password.

## 6. Check the consumer group

```bash
docker compose run --rm --no-deps notify-worker python -c "import os, redis; r = redis.from_url(os.environ['REDIS_URL']); s = os.environ['EJUDGE_NOTIFY_STREAM']; print('entries:', r.xlen(s)); print('groups:', r.xinfo_groups(s) if r.exists(s) else 'stream does not exist yet')"
```

- **Group `rmatics` is listed:** nothing to do. The worker continues where
  the group left off.
- **Stream does not exist, or is empty:** nothing to do. The worker creates
  the stream and group on start.
- **Stream has entries but there is no `rmatics` group:** the worker would
  create the group at id `0` and **re-send the whole stream history** to
  rmatics. Unless that is what you want, create the group at the end of the
  stream first:

  ```bash
  docker compose run --rm --no-deps notify-worker python -c "import os, redis; r = redis.from_url(os.environ['REDIS_URL']); r.xgroup_create(os.environ['EJUDGE_NOTIFY_STREAM'], os.environ['EJUDGE_NOTIFY_GROUP'], id='\$', mkstream=True); print('created')"
  ```

## 7. Start

```bash
docker compose up -d
```

The service has `restart: unless-stopped`, so it comes back after a crash or a
reboot, as long as the Docker service is enabled (`sudo systemctl enable docker`).

## 8. Verify

```bash
docker compose ps
docker compose logs --tail 50 notify-worker
```

Expect the container to be `running`, and this line in the log:

```
[...] INFO in worker: Worker 1 started
```

Submit a run in ejudge and check that its status updates in rmatics. Each
notification is logged as `received message {...}`, followed by
`informatics response: <Response [200]>` when rmatics accepted it.

`Notify worker 1 failed, retrying in Ns` means Redis is unreachable. The
worker keeps retrying, waiting up to 30s between attempts, and recovers
without a restart once Redis is back. If it doesn't clear, go back to step 5.

`notify-worker: failed to process message` means the POST to rmatics failed.
**That notification is lost** (the message is acknowledged anyway). The
status code in the traceback tells why:

| Status | Cause |
|---|---|
| `401` / `403` | `EJUDGE_API_TOKEN` doesn't match `JUDGE_ID` in rmatics' `judges.json`, or `JUDGE_ID` is empty, not a number or unknown to rmatics. `EJUDGE_API_TOKEN is not configured` in the log means the token is empty. |
| `400` | rmatics rejected the payload (a run without `run_id`, `contest_id` or `status`). |
| `404` | Wrong `RMATICS_ALIVE_URL`, or the pynformatics proxy isn't deployed yet. |
| `502` | The pynformatics proxy can't reach rmatics. |
| timeout / connection error | `RMATICS_ALIVE_URL` host unreachable from this node (step 5). |

## Updating

```bash
cd /opt/notify-worker/deploy
git pull --ff-only
docker compose up -d --build
docker compose logs --tail 50 notify-worker
```

If `git pull --ff-only` refuses, someone changed files on the node. Look at
them with `git status` before discarding anything.

## Rolling back

```bash
git log --oneline -5
git checkout <previous-commit>
docker compose up -d --build
```

Go back to the branch with `git checkout master` when the fix is released.

## Stopping

```bash
docker compose down
```

The Redis stream and group are kept. Notifications sent while the worker is
stopped are delivered when it starts again.
