param(
    [string]$DataDir = '..\Partitioned LCL Data\Small LCL Data',
    [string]$JavaHome = '',
    [switch]$AggregateOnly
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($JavaHome) { $env:JAVA_HOME = (Resolve-Path -LiteralPath $JavaHome).Path }
elseif (Test-Path -LiteralPath '..\runtime') {
    $lclJdk = Get-ChildItem -LiteralPath '..\runtime' -Directory -Filter 'jdk-21*' | Select-Object -First 1
    if ($lclJdk) { $env:JAVA_HOME = $lclJdk.FullName }
}
$env:SPARK_LOCAL_IP = '127.0.0.1'
$lclPython = '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $lclPython)) { $lclPython = '.\.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $lclPython)) { throw 'Buat .venv dan instal requirements.txt dahulu; lihat README.' }
$lclPythonAbs = (Resolve-Path -LiteralPath $lclPython).Path
$env:PATH = (Split-Path -Parent $lclPythonAbs) + ';' + $env:PATH
$env:PYSPARK_PYTHON = 'python'
$env:PYSPARK_DRIVER_PYTHON = 'python'
if ($AggregateOnly) {
    & $lclPython src\experiment.py --aggregate results\aggregate_2013.csv --output .
} else {
    & $lclPython src\experiment.py --data-dir $DataDir --output . --files 3 --households 50
}
if ($LASTEXITCODE -ne 0) { throw 'Eksperimen gagal; periksa logs dan versi Java.' }
& $lclPython src\verify_results.py
if ($LASTEXITCODE -ne 0) { throw 'Pemeriksaan hasil gagal.' }
& $lclPython src\make_report.py
if ($LASTEXITCODE -ne 0) { throw 'Pembuatan laporan gagal.' }
