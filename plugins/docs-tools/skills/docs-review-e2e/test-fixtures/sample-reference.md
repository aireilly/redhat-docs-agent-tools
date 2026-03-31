---
title: CLI Reference
description: Command-line reference for the example-tool CLI.
---

# CLI Reference

## Installation

```bash
$ pip3 install example-tool
```

## Commands

### `example-tool init`

Initialize a new project:

```bash
$ example-tool init --name my-project --template default
```

### `example-tool deploy`

Deploy the application:

```bash
$ example-tool deploy --env production --replicas 3 --timeout 300
```

### `example-tool status`

Check deployment status:

```bash
$ example-tool status --format json | jq '.deployments[]'
```

## Configuration

Create a `config.toml` file:

```toml
[server]
host = "0.0.0.0"
port = 8080
workers = 4

[database]
url = "postgresql://localhost:5432/mydb"
pool_size = 10

[logging]
level = "info"
format = "json"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXAMPLE_API_KEY` | API authentication key | (required) |
| `EXAMPLE_LOG_LEVEL` | Log verbosity | `info` |
| `EXAMPLE_TIMEOUT` | Request timeout in seconds | `30` |
