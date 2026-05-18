<#
.SYNOPSIS
    Create the mandatory runtime root for the AI Manager Platform.

.DESCRIPTION
    Idempotently creates:

        C:\Users\ASUS\Desktop\AI Manager\
            KB\Regulator\{lex_uz,cbu_uz,ipakyulibank}
            KB\Lotus
            KB\Processed
            KB\Raw
            KB\Temp
            Archive
            Logs\{agents,pipeline,api,audit}
            Cache\{embeddings,ocr,responses}

    Then tightens ACLs on KB\Lotus so only the current user (operator) and
    SYSTEM can read it. Re-run safely; existing data is preserved.

.PARAMETER Root
    Override the runtime root (used in CI or dev). Defaults to the
    mandatory operator path.
#>

[CmdletBinding()]
param(
    [string]$Root = 'C:\Users\ASUS\Desktop\AI Manager'
)

$ErrorActionPreference = 'Stop'

$dirs = @(
    'KB\Regulator\lex_uz',
    'KB\Regulator\cbu_uz',
    'KB\Regulator\ipakyulibank',
    'KB\Lotus',
    'KB\Processed',
    'KB\Raw',
    'KB\Temp',
    'Archive',
    'Logs\agents',
    'Logs\pipeline',
    'Logs\api',
    'Logs\audit',
    'Cache\embeddings',
    'Cache\ocr',
    'Cache\responses'
)

Write-Host "AI Manager root: $Root"

if (-not (Test-Path -LiteralPath $Root)) {
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    Write-Host "  + created root"
}

foreach ($d in $dirs) {
    $full = Join-Path -Path $Root -ChildPath $d
    if (-not (Test-Path -LiteralPath $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Host "  + $d"
    }
}

# Lotus ACL: remove inherited "Users" access; keep current user + SYSTEM.
$lotus = Join-Path -Path $Root -ChildPath 'KB\Lotus'
$acl = Get-Acl -LiteralPath $lotus
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { [void]$acl.RemoveAccessRule($_) }

$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$rules = @(
    New-Object System.Security.AccessControl.FileSystemAccessRule(
        $me, 'FullControl',
        'ContainerInherit,ObjectInherit', 'None', 'Allow'),
    New-Object System.Security.AccessControl.FileSystemAccessRule(
        'NT AUTHORITY\SYSTEM', 'FullControl',
        'ContainerInherit,ObjectInherit', 'None', 'Allow')
)
foreach ($r in $rules) { $acl.AddAccessRule($r) }
Set-Acl -LiteralPath $lotus -AclObject $acl
Write-Host "  * locked ACL on KB\Lotus"

Write-Host "Done."
