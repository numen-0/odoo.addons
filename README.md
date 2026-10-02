# odoo.addons

A small collection of custom **Odoo addons**.

> **Odoo version**:
>
> This repository currently targets **Odoo 18**, mainly because it was the
> version I found useful Python stubs for during development.

## Addons

| name | description | status |
|:-----|:------------|:------:|
| [`oslo`](/addons/oslo) | Production uptime tracker | `v18.0.1.0.0` |

## Local development

```sh
docker compose up
```

> Odoo will be served [here](http://localhost:8069).

```sh
uv sync
```

> **Trick**:
>
> To check the Python version used by Odoo:
>
> ```sh
> docker compose exec odoo python3 --version
> ```

## License

All the repo falls under the [MIT License](/LICENSE).


