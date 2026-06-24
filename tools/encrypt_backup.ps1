param(
  [Parameter(Mandatory=$true)][string]$InputPath,
  [Parameter(Mandatory=$false)][string]$OutputPath = "",
  [Parameter(Mandatory=$true)][string]$Passphrase
)
if (-not (Test-Path $InputPath)) { throw "InputPath bulunamadı: $InputPath" }
if (-not $OutputPath) { $OutputPath = "$InputPath.enc" }
$bytes = [IO.File]::ReadAllBytes((Resolve-Path $InputPath))
$salt = New-Object byte[] 16
$rng = [Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($salt)
$derive = [Security.Cryptography.Rfc2898DeriveBytes]::new($Passphrase, $salt, 200000, [Security.Cryptography.HashAlgorithmName]::SHA256)
$key = $derive.GetBytes(32)
$aes = [Security.Cryptography.Aes]::Create(); $aes.Key = $key; $aes.GenerateIV(); $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'
$enc = $aes.CreateEncryptor().TransformFinalBlock($bytes,0,$bytes.Length)
$out = [byte[]](0x4d,0x45,0x44,0x45,0x4b,0x45,0x4e,0x43) + $salt + $aes.IV + $enc
[IO.File]::WriteAllBytes($OutputPath,$out)
Write-Host "Şifreli yedek oluşturuldu: $OutputPath"
