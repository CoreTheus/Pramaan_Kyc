$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$python = Join-Path (Split-Path $project -Parent) '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$output = Join-Path (Split-Path $project -Parent) 'release/SmartKYC'
$build = Join-Path (Split-Path $project -Parent) 'build'
New-Item -ItemType Directory -Force -Path $output, $build | Out-Null
& $python -m PyInstaller --noconfirm --onefile --console --name SmartKYC_Server --distpath $output --workpath "$build/server" --specpath $build "$project/server.py"
if ($LASTEXITCODE -ne 0) { throw 'Server packaging failed' }
& $python -m PyInstaller --noconfirm --onefile --windowed --name SmartKYC_Client --distpath $output --workpath "$build/client" --specpath $build "$project/client.py"
if ($LASTEXITCODE -ne 0) { throw 'Client packaging failed' }
& $python -m PyInstaller --noconfirm --onefile --windowed --name SmartKYC_SampleBuilder --distpath $output --workpath "$build/builder" --specpath $build "$project/sample_builder.py"
if ($LASTEXITCODE -ne 0) { throw 'Sample Builder packaging failed' }
foreach ($file in @('config.json','setup.bat','start_server.bat','start_client.bat','README.txt','DEMO.txt')) {
  Copy-Item -LiteralPath (Join-Path $project $file) -Destination $output -Force
}
foreach ($folder in @('ui','ml')) {
  Copy-Item -LiteralPath (Join-Path $project $folder) -Destination $output -Recurse -Force
}
New-Item -ItemType Directory -Force -Path "$output/data" | Out-Null
Copy-Item -LiteralPath "$project/data/demo" -Destination "$output/data" -Recurse -Force
Copy-Item -LiteralPath "$project/data/synthetic_dataset.csv" -Destination "$output/data" -Force
Write-Output "Ready: $output (copy the entire folder)."
