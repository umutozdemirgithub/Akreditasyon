param(
  [string]$Output = ""
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($Output) {
  python "$Root\tools\make_release_zip.py" --output $Output
} else {
  python "$Root\tools\make_release_zip.py"
}
