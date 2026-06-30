# Quick install for the goph CLI (Windows).
#   irm https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.ps1 | iex
#
# Override the install location with the InstallDir env var (default:
# %LOCALAPPDATA%\Programs\goph):
#   $Env:InstallDir = "C:\tools\goph"; irm .../install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "svetlana1959/GophKeeper"
$Binary = "goph"
$InstallDir = if ($Env:InstallDir) { $Env:InstallDir } else { Join-Path $Env:LOCALAPPDATA "Programs\$Binary" }

# --- detect arch (normalise to GoReleaser's goarch names) ------------------
switch ($Env:PROCESSOR_ARCHITECTURE) {
	"AMD64" { $Arch = "amd64" }
	"ARM64" { $Arch = "arm64" }
	default { throw "Unsupported architecture: $Env:PROCESSOR_ARCHITECTURE" }
}

# --- resolve the latest release tag via the GitHub API ---------------------
$Tag = (Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest").tag_name
if (-not $Tag) { throw "Could not determine the latest release tag." }
$Version = $Tag.TrimStart("v") # archive names drop the leading "v"

# --- build the download URL (matches .goreleaser.yaml name_template) -------
$Asset = "${Binary}_${Version}_windows_${Arch}.zip"
$Url = "https://github.com/$Repo/releases/download/$Tag/$Asset"

Write-Host "Installing $Binary $Tag (windows/$Arch)..."

# --- download + extract into a temp dir we always clean up -----------------
$Tmp = Join-Path $Env:TEMP "${Binary}_$([System.Guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null
try {
	$Zip = Join-Path $Tmp $Asset
	Invoke-WebRequest -Uri $Url -OutFile $Zip
	Expand-Archive -Path $Zip -DestinationPath $Tmp -Force

	New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
	Copy-Item -Path (Join-Path $Tmp "$Binary.exe") -Destination $InstallDir -Force
}
finally {
	Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}

Write-Host "Installed $Binary to $InstallDir\$Binary.exe"

# --- add the install dir to the user PATH if it isn't already there --------
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($UserPath -split ";") -notcontains $InstallDir) {
	[Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
	Write-Host "Added $InstallDir to your user PATH. Restart your terminal to pick it up."
}
