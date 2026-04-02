#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


USERNAME = "LucasLouvem"
API_BASE = "https://api.github.com"
OUTPUT_LIGHT = Path("assets/profile-light.svg")
OUTPUT_DARK = Path("assets/profile-dark.svg")


def request_json(url: str, token: str | None, data: dict | None = None) -> dict | list:
    payload = None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lucaslouvem-readme-panel",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_user(token: str | None) -> dict:
    data = request_json(f"{API_BASE}/users/{USERNAME}", token)
    if not isinstance(data, dict):
        raise RuntimeError("Falha ao obter dados do usuario.")
    return data


def fetch_repos(token: str | None) -> list[dict]:
    repos: list[dict] = []
    page = 1
    per_page = 100
    while True:
        batch = request_json(
            f"{API_BASE}/users/{USERNAME}/repos?per_page={per_page}&page={page}&type=owner&sort=updated",
            token,
        )
        if not isinstance(batch, list):
            raise RuntimeError("Falha ao obter repositorios.")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return repos


def fetch_contributions_this_year(token: str | None) -> int | None:
    if not token:
        return None

    now = datetime.now(timezone.utc)
    start = datetime(now.year, 1, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    end = now.isoformat().replace("+00:00", "Z")

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {"login": USERNAME, "from": start, "to": end},
    }
    data = request_json(f"{API_BASE}/graphql", token, payload)
    if not isinstance(data, dict):
        return None
    return (
        data.get("data", {})
        .get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("totalContributions")
    )


def format_date(date_string: str | None) -> str:
    if not date_string:
        return "-"
    value = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return value.strftime("%d/%m/%Y")


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def kv(label: str, value: str, width: int = 16) -> str:
    dots = "." * max(2, width - len(label))
    return f"{label} {dots} {value}"


def build_lines(user: dict, repos: list[dict], contributions: int | None) -> list[str]:
    own_repos = [repo for repo in repos if not repo.get("fork")]
    languages = Counter(
        str(repo["language"])
        for repo in own_repos
        if repo.get("language")
    )
    top_languages = ", ".join(language for language, _ in languages.most_common(3)) or "-"
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in own_repos)
    latest_push = format_date(max((repo.get("pushed_at") for repo in repos), default=None))
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    return [
        f"{USERNAME.lower()}@github",
        "------------------------------",
        kv("cargo", "Full Stack Junior"),
        kv("foco", "Back-end, AppSec"),
        kv("stack", "Python, Django, PostgreSQL, Docker"),
        kv("base", "Infra, redes, acessos"),
        "",
        kv("seguranca", "Desenvolvimento seguro"),
        kv("trilha", "DevSecOps em formacao"),
        kv("comunidade", "DESEC, Hackerclub, THM, HTB"),
        kv("destaque", "1o lugar no CTF BSidesRJ"),
        "",
        kv("repos", str(len(own_repos))),
        kv("seguidores", str(user.get("followers", 0))),
        kv("estrelas", str(stars)),
        kv("contribuicoes", str(contributions) if contributions is not None else "-"),
        kv("linguagens", top_languages),
        kv("ultimo push", latest_push),
        kv("atualizado", today),
    ]


def make_svg(theme: dict[str, str], lines: list[str]) -> str:
    left_header = "lucas@louvem"
    left_subheader = "profile --fetch"
    left_tags = [
        "fullstack + appsec",
        "infra + devsecops",
    ]

    left_texts: list[str] = []
    left_texts.append(
        f'<text x="56" y="74" class="mono" fill="{theme["accent"]}" font-weight="700">{escape_xml(left_header)}</text>'
    )
    left_texts.append(
        f'<text x="56" y="98" class="mono" fill="{theme["logo"]}">{escape_xml(left_subheader)}</text>'
    )
    tag_y = 142
    for tag in left_tags:
        left_texts.append(
            f'<rect x="56" y="{tag_y - 16}" width="170" height="26" rx="6" fill="{theme["tag_bg"]}" stroke="{theme["border"]}"/>'
        )
        left_texts.append(
            f'<text x="68" y="{tag_y + 1}" class="mono" fill="{theme["logo"]}">{escape_xml(tag)}</text>'
        )
        tag_y += 34

    right_texts: list[str] = []
    y = 44
    for index, line in enumerate(lines):
        fill = theme["accent"] if index == 0 else theme["text"]
        weight = "700" if index in {0, 1} else "400"
        right_texts.append(
            f'<text x="350" y="{y}" class="mono" fill="{fill}" font-weight="{weight}">{escape_xml(line)}</text>'
        )
        y += 22

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="980" height="460" viewBox="0 0 980 460" role="img" aria-labelledby="title desc">
  <title id="title">README terminal de {USERNAME}</title>
  <desc id="desc">Painel simples com informacoes de perfil e estatisticas publicas do GitHub.</desc>
  <style>
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 16px;
    }}
  </style>
  <rect width="980" height="460" rx="18" fill="{theme["bg"]}"/>
  <rect x="10" y="10" width="960" height="440" rx="12" fill="none" stroke="{theme["border"]}"/>
  <rect x="36" y="36" width="230" height="164" rx="10" fill="none" stroke="{theme["border"]}"/>
  <line x1="36" y1="58" x2="266" y2="58" stroke="{theme["border"]}"/>
  <circle cx="54" cy="47" r="3" fill="{theme["dot_1"]}"/>
  <circle cx="66" cy="47" r="3" fill="{theme["dot_2"]}"/>
  <circle cx="78" cy="47" r="3" fill="{theme["dot_3"]}"/>
  {''.join(left_texts)}
  {''.join(right_texts)}
</svg>
"""


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    token = os.getenv("GITHUB_TOKEN")
    user = fetch_user(token)
    repos = fetch_repos(token)
    contributions = fetch_contributions_this_year(token)

    lines = build_lines(user, repos, contributions)

    light = {
        "bg": "#f6f8fa",
        "border": "#d0d7de",
        "text": "#24292f",
        "accent": "#0969da",
        "logo": "#1f2328",
        "tag_bg": "#f3f4f6",
        "dot_1": "#ff5f56",
        "dot_2": "#ffbd2e",
        "dot_3": "#27c93f",
    }
    dark = {
        "bg": "#0d1117",
        "border": "#30363d",
        "text": "#c9d1d9",
        "accent": "#58a6ff",
        "logo": "#8b949e",
        "tag_bg": "#161b22",
        "dot_1": "#ff5f56",
        "dot_2": "#ffbd2e",
        "dot_3": "#27c93f",
    }

    write_svg(OUTPUT_LIGHT, make_svg(light, lines))
    write_svg(OUTPUT_DARK, make_svg(dark, lines))
    print(f"Arquivos gerados: {OUTPUT_LIGHT} e {OUTPUT_DARK}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        print(f"Erro HTTP {exc.code}: {body}")
        raise
    except urllib.error.URLError as exc:
        print(f"Erro de rede: {exc}")
        raise
