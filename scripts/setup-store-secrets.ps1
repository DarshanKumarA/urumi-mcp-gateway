#Requires -Version 7.0
<#
.SYNOPSIS
Prepares only the four local store Secrets; never creates the namespace.
.DESCRIPTION
Validate (default): offline fixtures and disposable RNG samples; no kubectl/prompt.
Check: read-only context, namespace and existing Secret checks; no generation.
Create: same preflight, then create missing Secrets only using JSON on stdin.
Run Create only after a separately authorized runtime-preparation review.
Do not dot-source, trace, debug, or transcript credential-bearing execution.
#>
[CmdletBinding()]
param(
    [ValidateSet('Validate', 'Check', 'Create')]
    [string] $Mode = 'Validate'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$script:TargetContext = 'k3d-urumi-local'
$script:TargetNamespace = 'urumi'
$script:Operation = 'initialization'
$script:KubectlPath = $null
$script:Utf8 = [System.Text.UTF8Encoding]::new($false, $true)

function Get-StoreContract {
    # 32 random bytes = 256 bits (44 base64 characters); auth uses 64 = 512 bits (88).
    # These are credential TEXT encodings, distinct from Kubernetes data encoding.
    @(
        @{ Name = 'urumi-mariadb-root'; Keys = @('root-password'); RandomBytes = 32 }
        @{ Name = 'urumi-store-db'; Keys = @('password'); RandomBytes = 32 }
        @{ Name = 'urumi-wordpress-admin'; Keys = @('admin-password'); RandomBytes = 0 }
        @{ Name = 'urumi-wordpress-auth'; RandomBytes = 64; Keys = @(
            'auth-key', 'secure-auth-key', 'logged-in-key', 'nonce-key',
            'auth-salt', 'secure-auth-salt', 'logged-in-salt', 'nonce-salt'
        ) }
    )
}

function Assert-CredentialText([string] $Text) {
    # WP-CLI consumes one stdin line; image _FILE readers trim trailing newlines.
    # Reject ambiguous input rather than silently changing the user's password.
    if ([string]::IsNullOrWhiteSpace($Text) -or $Text -match '[\x00\r\n]' -or $Text -cne $Text.Trim()) {
        throw 'Credential must be nonempty single-line text without NUL or edge whitespace.'
    }
}

function New-RandomCredential([int] $ByteCount) {
    $bytes = [byte[]]::new($ByteCount)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
        return [Convert]::ToBase64String($bytes)
    }
    finally {
        [Array]::Clear($bytes, 0, $bytes.Length)
        $rng.Dispose()
    }
}

function ConvertTo-SecretData([string] $Text) {
    Assert-CredentialText $Text
    $bytes = $script:Utf8.GetBytes($Text)
    try { return [Convert]::ToBase64String($bytes) }
    finally { [Array]::Clear($bytes, 0, $bytes.Length) }
}

function Assert-StoreSecret($Secret, $Contract) {
    if ($Secret -isnot [System.Collections.IDictionary] -or
        $Secret.apiVersion -cne 'v1' -or $Secret.kind -cne 'Secret' -or
        $Secret.type -cne 'Opaque' -or $Secret.metadata.name -cne $Contract.Name -or
        $Secret.metadata.namespace -cne $script:TargetNamespace -or
        $Secret.metadata['deletionTimestamp'] -or
        $Secret.data -isnot [System.Collections.IDictionary]) {
        throw 'Secret identity, type, lifecycle or data is inconsistent.'
    }
    # The helper owns exactly this key contract. Extra/missing keys require review.
    if (@(Compare-Object @($Secret.data.psbase.Keys) $Contract.Keys -CaseSensitive).Count -ne 0) {
        throw 'Secret key set differs.'
    }
    foreach ($key in $Contract.Keys) {
        if (-not $Secret.data.Contains($key) -or $Secret.data[$key] -isnot [string]) {
            throw 'Required Secret key is missing or invalid.'
        }
        $bytes = $null
        $text = $null
        try {
            $bytes = [Convert]::FromBase64String($Secret.data[$key])
            $text = $script:Utf8.GetString($bytes)
            Assert-CredentialText $text
        }
        finally {
            if ($null -ne $bytes) { [Array]::Clear($bytes, 0, $bytes.Length) }
            $text = $null
        }
    }
}

function New-SecretJson($Contract, [System.Collections.IDictionary] $Data) {
    $secret = @{
        apiVersion = 'v1'; kind = 'Secret'; type = 'Opaque'
        metadata = @{ name = $Contract.Name; namespace = $script:TargetNamespace }
        data = $Data
    }
    Assert-StoreSecret $secret $Contract
    return ConvertTo-Json -InputObject $secret -Depth 6 -Compress
}

function Invoke-StoreKubectl {
    param([string[]] $Arguments, [string] $InputJson = '', [switch] $ReadOutput)
    # Only fixed, non-secret arguments go on the process command line. Never use a shell.
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $script:KubectlPath
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardInputEncoding = $script:Utf8
    $info.StandardOutputEncoding = $script:Utf8
    foreach ($argument in (@(('--context=' + $script:TargetContext),
        ('--namespace=' + $script:TargetNamespace), '--request-timeout=15s', '--v=0') + $Arguments)) {
        $info.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $info
    $started = $false
    $output = $null
    $outputTask = $null
    $errorTask = $null
    try {
        $started = $process.Start()
        if (-not $started) { throw 'kubectl did not start.' }
        # Drain both pipes concurrently. Raw stderr is discarded, even on failure.
        $outputTask = $process.StandardOutput.ReadToEndAsync()
        $errorTask = $process.StandardError.BaseStream.CopyToAsync([System.IO.Stream]::Null)
        $writeTask = $process.StandardInput.WriteAsync($InputJson)
        if (-not $writeTask.Wait(10000)) { throw 'kubectl stdin timed out.' }
        [void] $writeTask.GetAwaiter().GetResult()
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'kubectl process timed out.' }
        if (-not $outputTask.Wait(1000) -or -not $errorTask.Wait(1000)) {
            throw 'kubectl output drain timed out.'
        }
        if ($process.ExitCode -ne 0) { throw 'kubectl returned failure.' }
        if ($ReadOutput) {
            $output = $outputTask.GetAwaiter().GetResult()
            return $output
        }
        # Create responses are never forwarded, regardless of their content.
    }
    finally {
        if ($started -and -not $process.HasExited) { $process.Kill($true) }
        $process.Dispose()
        $output = $null
        $outputTask = $null
        $errorTask = $null
        $InputJson = $null
    }
}

function Get-ExistingStoreSecret($Contract) {
    $script:Operation = 'checking Secret ' + $Contract.Name + ' (explicit repair required if inconsistent)'
    $raw = $null
    $secret = $null
    try {
        $raw = Invoke-StoreKubectl -Arguments @('get', 'secret', $Contract.Name,
            '--ignore-not-found=true', '--output=json') -ReadOutput
        # Only successful, empty output means absent; other kubectl failures throw.
        if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
        $secret = ConvertFrom-Json -InputObject $raw -AsHashtable
        Assert-StoreSecret $secret $Contract
        return $true
    }
    finally { $raw = $null; $secret = $null }
}

function Invoke-OfflineValidation {
    $script:Operation = 'offline validation'
    # Test RNG machinery only: disposable samples never enter a Secret or kubectl.
    foreach ($size in @(32, 64)) {
        $sample = $null
        $bytes = $null
        try {
            $sample = New-RandomCredential $size
            $bytes = [Convert]::FromBase64String($sample)
            if ($bytes.Length -ne $size) { throw 'RNG sample length mismatch.' }
        }
        finally {
            if ($null -ne $bytes) { [Array]::Clear($bytes, 0, $bytes.Length) }
            $sample = $null
        }
    }
    # Only an obvious non-secret fixture is serialized; never generated credentials.
    foreach ($contract in @(Get-StoreContract)) {
        $data = @{}
        foreach ($key in $contract.Keys) { $data[$key] = ConvertTo-SecretData 'TEST-ONLY-NOT-A-CREDENTIAL' }
        $json = New-SecretJson $contract $data
        $fixture = ConvertFrom-Json -InputObject $json -AsHashtable
        Assert-StoreSecret $fixture $contract
        $key = $contract.Keys[0]
        foreach ($bad in @('missing', 'empty', 'invalid-base64', 'wrong-type', 'wrong-namespace', 'extra-key', 'wrong-case')) {
            $candidate = ConvertFrom-Json -InputObject $json -AsHashtable
            switch ($bad) {
                'missing' { [void] $candidate.data.Remove($key) }
                'empty' { $candidate.data[$key] = '' }
                'invalid-base64' { $candidate.data[$key] = '!' }
                'wrong-type' { $candidate.type = 'kubernetes.io/tls' }
                'wrong-namespace' { $candidate.metadata.namespace = 'test-only-other' }
                'extra-key' { $candidate.data['unexpected'] = $data[$key] }
                'wrong-case' { [void] $candidate.data.Remove($key); $candidate.data[$key.ToUpperInvariant()] = $data[$key] }
            }
            $rejected = $false
            try { Assert-StoreSecret $candidate $contract }
            catch { $rejected = $true }
            if (-not $rejected) { throw 'Invalid fixture was accepted.' }
        }
        Write-Host ($contract.Name + ': offline manifest/key validation passed.')
    }
    foreach ($invalid in @('', ' ', ' edge', 'edge ', "line`nbreak", "nul`0byte")) {
        $rejected = $false
        try { Assert-CredentialText $invalid } catch { $rejected = $true }
        if (-not $rejected) { throw 'Invalid credential text was accepted.' }
    }
    Write-Host 'Offline validation passed; no kubectl, prompt, files, or project credentials used.'
}

$adminInput = $null
$adminPointer = [IntPtr]::Zero
$plain = $null
$data = $null
$payload = $null
try {
    Write-Host ('Target context: ' + $script:TargetContext + '; namespace: ' + $script:TargetNamespace)
    if ($Mode -eq 'Validate') {
        Invoke-OfflineValidation
    }
    else {
        $script:Operation = 'locating kubectl'
        $script:KubectlPath = (Get-Command kubectl -CommandType Application -ErrorAction Stop).Source
        $script:Operation = 'verifying context k3d-urumi-local'
        $context = Invoke-StoreKubectl -Arguments @('config', 'get-contexts',
            $script:TargetContext, '--output=name') -ReadOutput
        if ($context.Trim() -cne $script:TargetContext) { throw 'Required context is absent.' }
        $script:Operation = 'verifying existing namespace urumi (must already exist and be Active)'
        $raw = Invoke-StoreKubectl -Arguments @('get', 'namespace', $script:TargetNamespace,
            '--output=json') -ReadOutput
        $namespace = ConvertFrom-Json -InputObject $raw -AsHashtable
        if ($namespace.kind -cne 'Namespace' -or $namespace.metadata.name -cne $script:TargetNamespace -or
            $namespace.status.phase -cne 'Active' -or $namespace.metadata['deletionTimestamp']) {
            throw 'Namespace is unavailable or terminating.'
        }
        $missing = @()
        # Validate ALL existing Secrets before prompting, generating or writing anything.
        foreach ($contract in @(Get-StoreContract)) {
            if (Get-ExistingStoreSecret $contract) {
                Write-Host ($contract.Name + ': preserved; required keys complete and valid.')
            }
            else {
                $missing += $contract
                Write-Host ($contract.Name + ': absent; would be created in Create mode.')
            }
        }
        if ($Mode -eq 'Create') {
            if (@($missing | Where-Object Name -eq 'urumi-wordpress-admin').Count -gt 0) {
                $script:Operation = 'reading initial WordPress admin password'
                $adminInput = Read-Host 'Choose the initial WordPress admin password (save it in your password manager)' -AsSecureString
                $adminPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminInput)
                $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adminPointer)
                Assert-CredentialText $plain
                $plain = $null
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPointer)
                $adminPointer = [IntPtr]::Zero
            }
            foreach ($contract in $missing) {
                $script:Operation = 'creating Secret ' + $contract.Name
                $data = @{}
                try {
                    foreach ($key in $contract.Keys) {
                        if ($contract.RandomBytes -eq 0) {
                            $adminPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminInput)
                            $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adminPointer)
                        }
                        else { $plain = New-RandomCredential $contract.RandomBytes }
                        $data[$key] = ConvertTo-SecretData $plain
                        $plain = $null
                        if ($adminPointer -ne [IntPtr]::Zero) {
                            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPointer)
                            $adminPointer = [IntPtr]::Zero
                        }
                    }
                    $payload = New-SecretJson $contract $data
                    # CREATE, never apply/replace/patch/delete; a concurrent creator causes failure.
                    Invoke-StoreKubectl -Arguments @('create', '-f', '-', '--output=name') -InputJson $payload
                    if (-not (Get-ExistingStoreSecret $contract)) { throw 'Created Secret was not found.' }
                    Write-Host ($contract.Name + ': created; required keys complete and valid.')
                }
                finally { $plain = $null; $payload = $null; $data = $null }
            }
        }
        Write-Host ($Mode + ' completed. Existing Secrets were not changed.')
    }
}
catch {
    # Never forward $_, Exception.Message, kubectl responses or JSON parsing errors.
    [Console]::Error.WriteLine('Store Secret preparation failed during ' + $script:Operation +
        '. No existing Secret was replaced or deleted. Review access/state and repair explicitly before retrying.')
    exit 1
}
finally {
    if ($adminPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPointer) }
    if ($null -ne $adminInput) { $adminInput.Dispose() }
    $plain = $null; $payload = $null; $data = $null
    # Mutable byte/BSTR buffers are cleared. Managed strings cannot be reliably zeroed.
}
