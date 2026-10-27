# Script para renderizar todos los diagramas .mmd a .pdf y .png usando mermaid-cli
$ErrorActionPreference = "Stop"

$diagramDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $diagramDir

Write-Host "Buscando diagramas .mmd en: $diagramDir"
$files = Get-ChildItem -Filter *.mmd

foreach ($file in $files) {
    $pdf = Join-Path $diagramDir ($file.BaseName + ".pdf")
    $png = Join-Path $diagramDir ($file.BaseName + ".png")
    
    Write-Host "Renderizando $($file.Name) -> $($file.BaseName).pdf ..."
    npx --yes @mermaid-js/mermaid-cli -i $file.FullName -o $pdf
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Fallo al renderizar PDF de $($file.Name)"
    }
    
    Write-Host "Renderizando $($file.Name) -> $($file.BaseName).png ..."
    npx --yes @mermaid-js/mermaid-cli -i $file.FullName -o $png
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Fallo al renderizar PNG de $($file.Name)"
    }
}

Write-Host "Renderizado de diagramas completado."
Pop-Location
