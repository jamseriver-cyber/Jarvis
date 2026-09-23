param(
    [string]$InnoSetupCompiler = "",
    [switch]$SkipInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "请先运行 Setup Jarvis.bat，创建项目虚拟环境。"
}

$distDir = Join-Path $projectRoot "dist"
$buildDir = Join-Path $projectRoot "build"
$pyiArgs = @(
    "-m", "PyInstaller", "--noconfirm",
    "--distpath", $distDir,
    "--workpath", $buildDir,
    (Join-Path $projectRoot "packaging\Jarvis.spec")
)

Push-Location $projectRoot
try {
    & $pythonExe @pyiArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败。" }

    $appExe = Join-Path $distDir "Jarvis\Jarvis.exe"
    $previewFile = Join-Path $buildDir "packaged-preview.png"
    if (Test-Path -LiteralPath $previewFile) {
        Remove-Item -LiteralPath $previewFile
    }
    $previewRun = Start-Process -FilePath $appExe -ArgumentList @(
        "--preview", "--screenshot", $previewFile
    ) -Wait -PassThru
    if ($previewRun.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $previewFile) -or
        (Get-Item -LiteralPath $previewFile).Length -eq 0) {
        throw "打包程序未能完成界面预览自检。"
    }
    Write-Host "可运行程序已通过启动自检：$appExe"

    if ($SkipInstaller) { return }

    if (-not $InnoSetupCompiler) {
        $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
        if ($command) { $InnoSetupCompiler = $command.Source }
    }
    if (-not $InnoSetupCompiler) {
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
        )
        $InnoSetupCompiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if (-not $InnoSetupCompiler -or -not (Test-Path -LiteralPath $InnoSetupCompiler)) {
        throw "已生成可运行程序，但未找到 Inno Setup 编译器 ISCC.exe；请安装 Inno Setup 6 后重试。"
    }

    & $InnoSetupCompiler (Join-Path $projectRoot "packaging\PersonalJarvis.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup 安装包编译失败。" }

    $installer = Join-Path $distDir "installer\PersonalJarvis-Setup-0.2.0-win64.exe"
    if (-not (Test-Path -LiteralPath $installer)) { throw "编译结束但未找到安装包。" }
    $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
    Write-Host "安装包：$installer"
    Write-Host "SHA-256：$digest"
} finally {
    Pop-Location
}
