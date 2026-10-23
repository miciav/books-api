# 📚 Books API

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)

A minimal REST service that performs **CRUD operations** (Create, Read, Update,
Delete) on a `books` table stored in **PostgreSQL**.

The whole service is a single Python file. Its purpose is to be a small, realistic
workload for practising **containerization and deployment** (Dockerfile,
Docker Compose, volumes, networks, restart policies, resource limits). You do
not need to change the code to run it in containers: everything is configured
through environment variables.

---

## Contents

- [At a glance](#at-a-glance)
- [Tech stack](#tech-stack)
- [Ports](#ports)
- [Environment variables](#environment-variables)
- [Database](#database)
- [API reference](#api-reference)
- [Testing the endpoints with curl](#testing-the-endpoints-with-curl)
- [Running locally without containers](#running-locally-without-containers)
- [Project structure](#project-structure)
- [License](#license)

---

## At a glance

| What                  | Value                                             |
|-----------------------|---------------------------------------------------|
| Language / runtime    | Python **3.12** (3.9+ works)                      |
| Dependencies          | `requirements.txt` (`pip install -r requirements.txt`) |
| Start command         | `python app.py`                                   |
| Service port          | **8000** (configurable with `APP_PORT`)           |
| Database              | **PostgreSQL 16** (official `postgres` image)     |
| Database port         | **5432**                                          |
| Health check endpoint | `GET /health`                                     |

## Tech stack

| Component  | Version | Notes                                                        |
|------------|---------|--------------------------------------------------------------|
| Python     | 3.12    | e.g. the `python:3.12-slim` image from Docker Hub            |
| Flask      | 3.1.2   | web framework                                                |
| psycopg    | 3.2.10  | PostgreSQL driver; the `[binary]` extra needs no compiler or system libraries |
| PostgreSQL | 16      | tested with `postgres:16-alpine`; any recent version (13+) should work |

## Ports

| Port   | Who listens          | Notes                                                  |
|--------|----------------------|--------------------------------------------------------|
| `8000` | the Books API        | HTTP. Change it with `APP_PORT`. The service binds to `0.0.0.0`, so it is reachable from outside a container. |
| `5432` | PostgreSQL           | Only the API needs to reach it. There is no need to publish it on the host. |

## Environment variables

### Service (Books API)

| Variable      | Default     | Description                              |
|---------------|-------------|------------------------------------------|
| `DB_HOST`     | `localhost` | Hostname of the PostgreSQL server. In Docker Compose, this is the **service name** of the database container. |
| `DB_PORT`     | `5432`      | Port of the PostgreSQL server            |
| `DB_NAME`     | `books`     | Name of the database                     |
| `DB_USER`     | `postgres`  | Database user                            |
| `DB_PASSWORD` | `postgres`  | Database password                        |
| `APP_PORT`    | `8000`      | Port the HTTP service listens on         |

### Database (official `postgres` image)

The official [`postgres`](https://hub.docker.com/_/postgres) image creates the
database and the user on first start from these variables. Their values
**must match** the `DB_*` variables of the service:

| `postgres` image variable | Must match       | Required |
|---------------------------|------------------|----------|
| `POSTGRES_PASSWORD`       | `DB_PASSWORD`    | **yes**: the container will not start without it |
| `POSTGRES_USER`           | `DB_USER`        | no (default `postgres`) |
| `POSTGRES_DB`             | `DB_NAME`        | no (defaults to the value of `POSTGRES_USER`) |

> ⚠️ These variables are only applied when the data directory is **empty**,
> i.e. the first time the database starts. If you change them later, delete
> the database volume first.

## Database

- **Data directory** (the path to persist with a volume):
  `/var/lib/postgresql/data`
- **Schema**: on startup, the service creates the table if it does not exist.
  No migrations or init scripts are needed.

  ```sql
  CREATE TABLE IF NOT EXISTS books (
      id     SERIAL PRIMARY KEY,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER
  );
  ```

- **Startup order**: on startup, the service retries the connection to the database
  **30 times, every 2 seconds** (about 60 s). If the database is still unreachable
  after that, the process exits with an error. A container restart policy
  (or a health check on the database) takes care of the rest.

## API reference

All request and response bodies are JSON.

| Method   | Path          | Request body                          | Success | Errors     |
|----------|---------------|---------------------------------------|---------|------------|
| `GET`    | `/health`     | –                                     | `200`   | `503` if the DB is down |
| `GET`    | `/books`      | –                                     | `200`   | –          |
| `GET`    | `/books/<id>` | –                                     | `200`   | `404`      |
| `POST`   | `/books`      | `title` *(req.)*, `author` *(req.)*, `year` | `201`   | `400`      |
| `PUT`    | `/books/<id>` | any subset of `title`, `author`, `year` | `200`   | `400`, `404` |
| `DELETE` | `/books/<id>` | –                                     | `204`   | `404`      |

A book looks like this:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965 }
```

## Testing the endpoints with curl

The service exposes **only a REST API**: there is no web page. You can test it
with `curl` from the machine where it runs, or from your laptop, using the VM's
IP address.

Set the base URL once:

```bash
BASE=http://localhost:8000          # on the VM itself
# BASE=http://<VM_IP>:8000          # from another machine
```

> 💡 Add `-i` to any command to see the HTTP status code and the headers, e.g.
> `curl -i $BASE/health`.

### Health check

```bash
curl $BASE/health
```
```text
{"database":"up","status":"ok"}                  # 200 OK
{"database":"down","status":"error"}             # 503 if the DB is unreachable
```

### Create books (`POST /books`)

```bash
curl -X POST $BASE/books \
     -H "Content-Type: application/json" \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

curl -X POST $BASE/books \
     -H "Content-Type: application/json" \
     -d '{"title": "Neuromancer", "author": "William Gibson", "year": 1984}'
```
```text
{"author":"Frank Herbert","id":1,"title":"Dune","year":1965}            # 201 Created
{"author":"William Gibson","id":2,"title":"Neuromancer","year":1984}    # 201 Created
```

### List all books (`GET /books`)

```bash
curl $BASE/books
```
```text
[{"author":"Frank Herbert","id":1,"title":"Dune","year":1965},{"author":"William Gibson","id":2,"title":"Neuromancer","year":1984}]
```

### Get one book (`GET /books/<id>`)

```bash
curl $BASE/books/1
```
```text
{"author":"Frank Herbert","id":1,"title":"Dune","year":1965}
```

### Update a book (`PUT /books/<id>`)

Only the fields you send are changed.

```bash
curl -X PUT $BASE/books/1 \
     -H "Content-Type: application/json" \
     -d '{"year": 1966}'
```
```text
{"author":"Frank Herbert","id":1,"title":"Dune","year":1966}
```

### Delete a book (`DELETE /books/<id>`)

```bash
curl -i -X DELETE $BASE/books/2
```
```text
HTTP/1.1 204 NO CONTENT                           # empty body
```

### Error cases

```bash
# Book that does not exist -> 404
curl $BASE/books/42
# {"error":"not found"}

# Missing required field -> 400
curl -X POST $BASE/books \
     -H "Content-Type: application/json" \
     -d '{"title": "Untitled"}'
# {"error":"'title' and 'author' are required"}

# Update with nothing to change -> 400
curl -X PUT $BASE/books/1 \
     -H "Content-Type: application/json" \
     -d '{}'
# {"error":"provide at least one of ['title', 'author', 'year']"}
```

> 💡 Pretty-print the JSON by piping it into `jq` (`curl -s $BASE/books | jq`)
> or `python3 -m json.tool`.

### Persistence check

The data must survive the containers being removed and created again:

1. create a few books with `POST /books`;
2. stop **and remove** the containers (e.g. `docker compose down`, without `-v`);
3. start them again;
4. run `curl $BASE/books`. If the database data is stored in a volume, the
   books are still there.

## Running locally without containers

You need Python 3.9+ and a reachable PostgreSQL server.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

DB_HOST=localhost DB_USER=postgres DB_PASSWORD=postgres DB_NAME=books \
python app.py
```

The service is then available at <http://localhost:8000/health>.

## Project structure

```text
.
├── app.py             # the whole service (routes + DB access)
├── requirements.txt   # Python dependencies (pinned)
├── LICENSE            # MIT
└── README.md
```

## License

Released under the [MIT License](LICENSE).
