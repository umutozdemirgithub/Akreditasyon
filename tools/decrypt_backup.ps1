param(
  [Parameter(Mandatory=$true)][string]$InputPath,
  [Parameter(Mandatory=$false)][string]$OutputPath = "",
  [Parameter(Mandatory=$true)][string]$Passphrase
)
if (-not (Test-Path $InputPath)) { throw "InputPath bulunamadı: $InputPath" }
if (-not $OutputPath) { $OutputPath = $InputPath -replace '\\.enc$','' }
$all = [IO.File]::ReadAllBytes((Resolve-Path $InputPath))
if ($all.Length -lt 40) { throw "Geçersiz şifreli yedek." }
$magic = [Text.Encoding]::ASCII.GetString($all[0..7])
if ($magic -ne 'MEDEKENC') { throw "Dosya MEDEK şifreli yedek formatında değil." }
$salt = $all[8..23]
$iv = $all[24..39]
$cipher = $all[40..($all.Length-1)]
$derive = [Security.Cryptography.Rfc2898DeriveBytes]::new($Passphrase, $salt, 200000, [Security.Cryptography.HashAlgorithmName]::SHA256)
$key = $derive.GetBytes(32)
$aes = [Security.Cryptography.Aes]::Create(); $aes.Key = $key; $aes.IV = $iv; $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'
$plain = $aes.CreateDecryptor().TransformFinalBlock($cipher,0,$cipher.Length)
[IO.File]::WriteAllBytes($OutputPath,$plain)
Write-Host "Yedek çözüldü: $OutputPath"
