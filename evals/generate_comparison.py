import json
from pathlib import Path
from typing import Any


DIRECTORY = Path(__file__).resolve().parent


def load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    if report.get("report_schema_version") != "2.0":
        raise ValueError(f"Schema incompatível em {path.name}.")
    return report


def comparison_markdown(legacy: dict[str, Any], lcel: dict[str, Any]) -> str:
    legacy_run, lcel_run = legacy["run"], lcel["run"]
    if legacy_run["dataset_sha256"] != lcel_run["dataset_sha256"]:
        raise ValueError("Os relatórios não usaram o mesmo dataset canônico.")
    if legacy_run["mode"] != lcel_run["mode"]:
        raise ValueError("Os relatórios não usaram o mesmo modo de execução.")

    metrics = (
        ("Qualidade (0-10)", "quality_0_10", False),
        ("Happy paths", "happy_path_success_rate", True),
        ("Structured output", "structured_output_rate", True),
        ("Recusas corretas", "refusal_rate", True),
        ("Encaminhamento profissional", "professional_referral_rate", True),
        ("Memória contextual", "memory_success_rate", True),
        ("Tokens por chamada", "tokens_average_per_model_call", False),
    )
    rows = []
    for label, key, percentage in metrics:
        before = legacy["summary"].get(key)
        after = lcel["summary"].get(key)
        formatter = (lambda value: "n/a" if value is None else f"{value * 100:.2f}%") if percentage else (
            lambda value: "n/a" if value is None else f"{value:.2f}"
        )
        delta = None if before is None or after is None else after - before
        rows.append(f"| {label} | {formatter(before)} | {formatter(after)} | {formatter(delta)} |")

    legacy_latency = legacy["summary"]["latency_model_calls"]["average_ms"]
    lcel_latency = lcel["summary"]["latency_model_calls"]["average_ms"]
    rows.append(
        f"| Latência real do modelo | {legacy_latency:.2f} ms | {lcel_latency:.2f} ms | "
        f"{lcel_latency - legacy_latency:.2f} ms |"
    )
    return "\n".join((
        "# Avaliação Antes/Depois",
        "",
        f"Dataset: `{legacy_run['dataset']}` (`{legacy_run['dataset_sha256']}`)",
        f"Modo: `{legacy_run['mode']}` | Modelo: `{legacy_run['model']}`",
        f"Legado: `{legacy_run['prompt']}` em {legacy_run['timestamp_utc']}",
        f"LCEL: `{lcel_run['prompt']}` em {lcel_run['timestamp_utc']}",
        "",
        "| Métrica | Antes (legado) | Depois (LCEL) | Delta |",
        "|---|---:|---:|---:|",
        *rows,
        "",
        "Valores negativos em tokens ou latência representam redução. O resultado de memória considera apenas turnos que exigem recuperação de contexto anterior.",
    )) + "\n"


def main() -> None:
    legacy = load_report(DIRECTORY / "legacy_results.json")
    lcel = load_report(DIRECTORY / "sprint3_results.json")
    output = DIRECTORY / "before_after.md"
    output.write_text(comparison_markdown(legacy, lcel), encoding="utf-8")
    print(f"Comparação gerada em {output.name}")


if __name__ == "__main__":
    main()
