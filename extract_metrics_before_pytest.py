"""Executa os testes do projeto com 'pixi run test' e salva os relatórios de testes e de cobertura.

Uso (sempre a partir da pasta raiz do projeto):

    python extract_metrics_pytest.py --etapa before    # antes da refatoração
    python extract_metrics_pytest.py --etapa after     # depois da refatoração
"""

# ======================= CONFIGURAÇÃO =======================
# Altere apenas estas duas linhas, se necessário.

# Pasta com o código-fonte do projeto (a cobertura é medida sobre ela).
CODIGO_FONTE = "dask"

# Pasta(s) dos testes. Se ficar como None, o script procura recursivamente
# todas as pastas "tests"/"test" espalhadas pelo projeto.
# Também aceita string ("dask/array/tests") ou lista (["dask/tests", "dask/array/tests"]).
TESTES = None
# ============================================================

import argparse
import os
import shutil
import subprocess
import sys

CANDIDATOS_TESTES = ["tests", "test", "src/tests", "src/test"]
PASTAS_IGNORADAS = {".git", ".pixi", ".venv", "venv", "__pycache__", "build", "dist", ".eggs"}
SUFIXO = {"before": "antes", "after": "depois"}


def descobrir_pastas_testes(codigo_fonte):
    """Procura recursivamente todas as pastas 'tests' ou 'test' dentro do projeto."""
    encontradas = []

    for raiz, dirs, _ in os.walk(codigo_fonte):
        dirs[:] = sorted(d for d in dirs if d not in PASTAS_IGNORADAS)
        for d in dirs:
            if d in ("tests", "test"):
                encontradas.append(os.path.join(raiz, d))

    if not encontradas:
        encontradas = [c for c in CANDIDATOS_TESTES if os.path.isdir(c)]

    return encontradas


def resolver_testes(config_testes, codigo_fonte):
    if config_testes is None:
        pastas = descobrir_pastas_testes(codigo_fonte)
    elif isinstance(config_testes, str):
        pastas = [config_testes]
    elif isinstance(config_testes, (list, tuple)):
        pastas = list(config_testes)
    else:
        sys.exit("[erro] formato inválido para TESTES. Use None, uma string ou uma lista de strings.")

    inexistentes = [p for p in pastas if not os.path.isdir(p)]
    if not pastas or inexistentes:
        sys.exit(
            f"[erro] pasta(s) de testes não encontrada(s): {inexistentes or CANDIDATOS_TESTES}. "
            f"Defina TESTES no início do script."
        )
    return pastas


def main():
    p = argparse.ArgumentParser(description="Extrai métricas de testes com pixi run test.")
    p.add_argument(
        "--etapa",
        choices=("before", "after"),
        required=True,
        help="before = antes da refatoração; after = depois da refatoração",
    )
    args = p.parse_args()

    if not CODIGO_FONTE:
        sys.exit("[erro] defina CODIGO_FONTE no início do script com a pasta do código-fonte do projeto.")
    if not os.path.isdir(CODIGO_FONTE):
        sys.exit(
            f"[erro] a pasta de código-fonte '{CODIGO_FONTE}' não existe. "
            f"Execute o script na pasta raiz do projeto e confira CODIGO_FONTE."
        )

    if not shutil.which("pixi"):
        sys.exit("[erro] executável 'pixi' não encontrado no PATH.")

    testes = resolver_testes(TESTES, CODIGO_FONTE)

    pasta = f"metrics-{args.etapa}-pytest"
    sufixo = SUFIXO[args.etapa]
    if os.path.exists(pasta):
        sys.exit(
            f"[erro] a pasta {pasta}/ já existe. Os resultados não serão sobrescritos.\n"
            f"       Se precisar refazer a medição, fale com o monitor antes de apagar a pasta."
        )
    os.makedirs(pasta)

    def saida(nome):
        return os.path.join(pasta, nome.format(s=sufixo))

    print(f"Etapa         : {args.etapa}")
    print(f"Código-fonte  : {CODIGO_FONTE}")
    print(f"Testes ({len(testes)})   : {', '.join(testes)}")
    print(f"Relatórios em : {pasta}/\n")

    resultado = subprocess.run([
        "pixi", "run", "test",
        *testes,
        "-v",
        "-p", "no:cacheprovider",                     # não cria a pasta .pytest_cache
        f"--junit-xml={saida('pytest_{s}.xml')}",
        f"--html={saida('pytest_{s}.html')}",
        "--self-contained-html",
        f"--cov={CODIGO_FONTE}",
        "--cov-branch",
        f"--cov-report=xml:{saida('coverage_{s}.xml')}",
        f"--cov-report=json:{saida('coverage_{s}.json')}",
        f"--cov-report=html:{saida('coverage_{s}_html')}",
        "--cov-report=term",
    ])

    # Códigos do pytest: 0 = todos passaram, 1 = algum teste falhou (resultado válido),
    # 2 = interrompido, 3 = erro interno, 4 = erro de uso, 5 = nenhum teste coletado.
    if resultado.returncode not in (0, 1):
        print(
            f"\n[aviso] 'pixi run test' terminou com código {resultado.returncode}: os testes não foram "
            f"executados corretamente (geralmente falta alguma dependência como pytest-cov ou pytest-html).\n"
            f"        Corrija o problema, apague a pasta {pasta}/ e execute o script novamente."
        )
        sys.exit(resultado.returncode)

    print(f"\nArquivos gerados em {pasta}/:")
    print(f"  pytest_{sufixo}.xml        resultados dos testes em XML")
    print(f"  pytest_{sufixo}.html       relatório visual dos testes")
    print(f"  coverage_{sufixo}.xml      cobertura de código em XML")
    print(f"  coverage_{sufixo}.json     cobertura de código em JSON")
    print(f"  coverage_{sufixo}_html/    relatório visual de cobertura")
    print("\nConcluído.")


if __name__ == "__main__":
    main()