# Um comando (Windows): garante o Python 3.11+ e delega tudo a tools/iniciar.py.
#   .\iniciar.ps1                 escritório ao vivo
#   .\iniciar.ps1 replay | dev | testes | docs | cli | instalar
# Se o PowerShell bloquear scripts: powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Encontrar-Python {
    foreach ($cmd in @(@("py", "-3.13"), @("py", "-3.12"), @("py", "-3.11"), @("python"), @("python3"))) {
        $exe = Get-Command $cmd[0] -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        $args_ = @($cmd | Select-Object -Skip 1) + @("-c", "import sys; print(sys.version_info >= (3, 11))")
        # Versão ausente (ex.: "py -3.13" sem o 3.13) escreve no stderr; no Windows PowerShell 5.1,
        # com ErrorActionPreference=Stop, isso vira erro fatal. Aqui é só "não serve": tenta a próxima.
        try { $ok = & $cmd[0] @args_ 2>$null } catch { $ok = $null }
        if ($ok -eq "True") { return ,$cmd }
    }
    return $null
}

$python = Encontrar-Python
if (-not $python) {
    Write-Host "==> Python 3.11+ não encontrado: instalando pelo winget (Python.Python.3.12)"
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Error "winget indisponível. Instale o Python 3.11+ em https://www.python.org/downloads/ e rode de novo."
    }
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $python = Encontrar-Python
    if (-not $python) { Write-Error "Python instalado, mas não encontrado no PATH: abra um novo terminal e rode de novo." }
}

$extra = @($python | Select-Object -Skip 1)
& $python[0] @extra "tools/iniciar.py" @args
exit $LASTEXITCODE
