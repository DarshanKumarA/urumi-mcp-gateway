#Requires -Version 7.0
<#
.SYNOPSIS
Prepares only the local WooCommerce REST Secret; never issues REST keys.
.DESCRIPTION
Validate (default) is completely offline: parser, manifest and mocked workflow checks.
Check inspects identity/type/key names only. Create preserves a valid existing Secret
or reads two masked inputs and submits an in-memory payload through kubectl stdin.
Check/Create require a separately authorized runtime step and an Active urumi namespace.
Use a trusted PowerShell 7 terminal without tracing, debugging or transcription.
Do not dot-source this script. No credential parameters or environment inputs exist.
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
$script:SecretName = 'urumi-woocommerce-rest'
$script:RequiredKeys = @('consumer-key', 'consumer-secret')
$script:Operation = 'initialization'
$script:KubectlPath = $null
$script:Utf8 = [System.Text.UTF8Encoding]::new($false, $true)

# kubectl receives the API object, but emits ONLY this projection, never data values.
# No annotations/labels or arbitrary messages are included. Key names are JSON-quoted.
$script:SecretProjection = '--output=go-template={"apiVersion":{{printf "%q" .apiVersion}},"kind":{{printf "%q" .kind}},"name":{{printf "%q" .metadata.name}},"namespace":{{printf "%q" .metadata.namespace}},"type":{{printf "%q" .type}},"terminating":{{if .metadata.deletionTimestamp}}true{{else}}false{{end}},"keys":[{{$sep := ""}}{{range $key, $ignored := .data}}{{$sep}}{{printf "%q" $key}}{{$sep = ","}}{{end}}]}'

function Assert-CredentialText([string] $Text) {
    # Shape validation is not proof that WooCommerce issued or accepts the credential.
    if ([string]::IsNullOrWhiteSpace($Text) -or $Text.Length -gt 1024 -or
        $Text -match '[\x00\r\n]' -or $Text -cne $Text.Trim()) {
        throw 'Credential text contract failed.'
    }
}

function ConvertTo-SecretData([string] $Text) {
    Assert-CredentialText $Text
    $bytes = $script:Utf8.GetBytes($Text)
    try { return [Convert]::ToBase64String($bytes) }
    finally { [Array]::Clear($bytes, 0, $bytes.Length) }
}

function Assert-RestSecretContract($Info) {
    if ($Info -isnot [System.Collections.IDictionary] -or
        $Info['apiVersion'] -cne 'v1' -or $Info['kind'] -cne 'Secret' -or
        $Info['name'] -cne $script:SecretName -or
        $Info['namespace'] -cne $script:TargetNamespace -or
        $Info['type'] -cne 'Opaque' -or $Info['terminating'] -isnot [bool] -or
        $Info['terminating'] -or $Info['keys'] -isnot [array] -or
        $Info['keys'].Count -ne 2) {
        throw 'Secret identity/type/lifecycle/key contract failed.'
    }
    if (@(Compare-Object $Info['keys'] $script:RequiredKeys -CaseSensitive).Count -ne 0) {
        throw 'Secret key contract failed.'
    }
}

function Get-ManifestContract($Manifest) {
    return @{
        apiVersion = $Manifest.apiVersion; kind = $Manifest.kind
        name = $Manifest.metadata.name; namespace = $Manifest.metadata.namespace
        type = $Manifest.type; terminating = [bool] $Manifest.metadata['deletionTimestamp']
        keys = @($Manifest.data.psbase.Keys)
    }
}

function New-RestSecretJson([System.Collections.IDictionary] $Data) {
    $manifest = @{
        apiVersion = 'v1'; kind = 'Secret'; type = 'Opaque'
        metadata = @{ name = $script:SecretName; namespace = $script:TargetNamespace }
        data = $Data
    }
    Assert-RestSecretContract (Get-ManifestContract $manifest)
    foreach ($key in $script:RequiredKeys) {
        if ($Data[$key] -isnot [string] -or [string]::IsNullOrEmpty($Data[$key])) {
            throw 'Manifest data contract failed.'
        }
    }
    return ConvertTo-Json -InputObject $manifest -Depth 5 -Compress
}

function Read-EncodedCredential([string] $KeyName) {
    $secure = $null
    $pointer = [IntPtr]::Zero
    $plain = $null
    try {
        # KeyName is supplied only from RequiredKeys, never from user input.
        $secure = Read-Host ('Enter the WooCommerce-issued ' + $KeyName) -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        return ConvertTo-SecretData $plain
    }
    finally {
        if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        if ($null -ne $secure) { $secure.Dispose() }
        $plain = $null
        # Managed plaintext/base64/JSON strings cannot be reliably zeroed.
    }
}

function Invoke-RestKubectl {
    param([string[]] $Arguments, [string] $InputJson = '', [switch] $ReadOutput)
    if ($Mode -eq 'Validate') { throw 'Real kubectl is prohibited during offline validation.' }
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
    $outputTask = $null
    $errorTask = $null
    try {
        $started = $process.Start()
        if (-not $started) { throw 'kubectl did not start.' }
        # Read output only for non-sensitive projections. Discard create stdout and ALL stderr.
        $outputTask = if ($ReadOutput) { $process.StandardOutput.ReadToEndAsync() }
            else { $process.StandardOutput.BaseStream.CopyToAsync([System.IO.Stream]::Null) }
        $errorTask = $process.StandardError.BaseStream.CopyToAsync([System.IO.Stream]::Null)
        $writeTask = $process.StandardInput.WriteAsync($InputJson)
        if (-not $writeTask.Wait(10000)) { throw 'kubectl stdin timed out.' }
        [void] $writeTask.GetAwaiter().GetResult()
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) { throw 'kubectl process timed out.' }
        if (-not $outputTask.Wait(1000) -or -not $errorTask.Wait(1000)) { throw 'kubectl output timed out.' }
        [void] $errorTask.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'kubectl returned failure.' }
        if ($ReadOutput) { return $outputTask.GetAwaiter().GetResult() }
        [void] $outputTask.GetAwaiter().GetResult()
    }
    finally {
        if ($started -and -not $process.HasExited) { $process.Kill($true) }
        $process.Dispose()
        $InputJson = $null; $outputTask = $null; $errorTask = $null
    }
}

function Test-ExistingRestSecret([scriptblock] $RunKubectl) {
    $script:Operation = 'checking Secret urumi-woocommerce-rest'
    $raw = & $RunKubectl -Arguments @('get', 'secret', $script:SecretName,
        '--ignore-not-found=true', $script:SecretProjection) -ReadOutput
    # Only SUCCESS plus empty output means absent. Transport/RBAC errors must throw.
    if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
    $contract = ConvertFrom-Json -InputObject $raw -AsHashtable
    Assert-RestSecretContract $contract
    return $true
}

function Invoke-RestSecretPreparation {
    param(
        [ValidateSet('Check', 'Create')] [string] $Action,
        [scriptblock] $RunKubectl,
        [scriptblock] $ReadCredential
    )
    # Injectable operations let Validate exercise this SAME workflow with offline fakes.
    $script:Operation = 'verifying context k3d-urumi-local'
    $context = & $RunKubectl -Arguments @('config', 'get-contexts', $script:TargetContext,
        '--output=name') -ReadOutput
    if ($context.Trim() -cne $script:TargetContext) { throw 'Required context is absent.' }
    $script:Operation = 'verifying Active namespace urumi'
    $phase = & $RunKubectl -Arguments @('get', 'namespace', $script:TargetNamespace,
        '--output=go-template={{if .metadata.deletionTimestamp}}Terminating{{else}}{{.status.phase}}{{end}}') -ReadOutput
    if ($phase.Trim() -cne 'Active') { throw 'Namespace is not Active.' }
    if (Test-ExistingRestSecret $RunKubectl) {
        return 'present; Opaque and exact key contract pass; preserved without changes.'
    }
    if ($Action -eq 'Check') { return 'absent; key contract cannot pass until created.' }

    $data = @{}
    $payload = $null
    try {
        foreach ($key in $script:RequiredKeys) {
            $script:Operation = 'masked credential input for Secret urumi-woocommerce-rest'
            $data[$key] = & $ReadCredential $key
        }
        $script:Operation = 'creating Secret urumi-woocommerce-rest'
        $payload = New-RestSecretJson $data
        # CREATE only: a concurrent creator fails rather than overwriting it.
        $null = & $RunKubectl -Arguments @('create', '-f', '-', '--output=name') -InputJson $payload
        if (-not (Test-ExistingRestSecret $RunKubectl)) { throw 'Created Secret was not found.' }
        return 'created; Opaque and exact key contract pass.'
    }
    finally {
        $payload = $null
        $data.Clear()
        $data = $null
    }
}

function Assert-Fixture([bool] $Passed) {
    if (-not $Passed) { throw 'Offline fixture failed.' }
    $script:Assertions++
}

function Invoke-OfflineValidation {
    $script:Operation = 'offline validation'
    $script:Assertions = 0
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath, [ref] $tokens, [ref] $parseErrors)
    Assert-Fixture ($parseErrors.Count -eq 0)
    $blocked = $false
    try { Invoke-RestKubectl -Arguments @('version') } catch { $blocked = $true }
    Assert-Fixture $blocked
    $fixtureData = @{}
    foreach ($key in $script:RequiredKeys) {
        $fixtureData[$key] = ConvertTo-SecretData ('TEST-ONLY-NOT-A-CREDENTIAL-' + $key)
    }
    $json = New-RestSecretJson $fixtureData
    $manifest = ConvertFrom-Json $json -AsHashtable
    $valid = Get-ManifestContract $manifest
    Assert-RestSecretContract $valid
    Assert-Fixture ($manifest.data['consumer-key'] -ceq $fixtureData['consumer-key'])
    Assert-Fixture ($manifest.data['consumer-secret'] -ceq $fixtureData['consumer-secret'])
    Assert-Fixture ($manifest.metadata.name -ceq $script:SecretName)
    foreach ($bad in @('api', 'kind', 'name', 'namespace', 'type', 'terminating', 'missing', 'extra', 'case', 'duplicate')) {
        $candidate = $valid.Clone()
        switch ($bad) {
            'api' { $candidate.apiVersion = 'v2' }
            'kind' { $candidate.kind = 'ConfigMap' }
            'name' { $candidate.name = 'test-only-other' }
            'namespace' { $candidate.namespace = 'test-only-other' }
            'type' { $candidate.type = 'kubernetes.io/tls' }
            'terminating' { $candidate.terminating = $true }
            'missing' { $candidate.keys = @('consumer-key') }
            'extra' { $candidate.keys = @('consumer-key', 'consumer-secret', 'extra') }
            'case' { $candidate.keys = @('Consumer-Key', 'consumer-secret') }
            'duplicate' { $candidate.keys = @('consumer-key', 'consumer-key') }
        }
        $rejected = $false
        try { Assert-RestSecretContract $candidate } catch { $rejected = $true }
        Assert-Fixture $rejected
    }
    foreach ($invalid in @('', ' ', ' edge', 'edge ', "line`nbreak", "line`rbreak", "nul`0byte", ('x' * 1025))) {
        $rejected = $false
        try { Assert-CredentialText $invalid } catch { $rejected = $true }
        Assert-Fixture $rejected
    }
    $validJson = ConvertTo-Json $valid -Compress
    foreach ($scenario in @('check-missing', 'check-present', 'create-present', 'create-missing',
        'conflict', 'read-failure', 'create-failure', 'postcheck-failure', 'no-context', 'no-namespace',
        'invalid-first-input', 'invalid-second-input')) {
        $state = @{ Reads = 0; Creates = 0; Prompts = [System.Collections.Generic.List[string]]::new() }
        # These scriptblocks never call an executable or read input; payloads are dummy only.
        $fakeRun = {
            param([string[]] $Arguments, [string] $InputJson = '', [switch] $ReadOutput)
            $commandText = $Arguments -join ' '
            Assert-Fixture (-not ($commandText.Contains('TEST-ONLY') -or
                $commandText.Contains($fixtureData['consumer-key']) -or
                $commandText.Contains($fixtureData['consumer-secret'])))
            if ($Arguments[0] -eq 'config') {
                if ($scenario -eq 'no-context') { return '' }
                return 'k3d-urumi-local'
            }
            if ($Arguments[0] -eq 'get' -and $Arguments[1] -eq 'namespace') {
                if ($scenario -eq 'no-namespace') { throw 'TEST-ONLY namespace unavailable' }
                return 'Active'
            }
            if ($Arguments[0] -eq 'get' -and $Arguments[1] -eq 'secret') {
                $state.Reads++
                Assert-Fixture ($Arguments[4] -ceq $script:SecretProjection)
                if ($scenario -eq 'read-failure') { throw 'TEST-ONLY read failure' }
                if ($scenario -eq 'conflict') { return $validJson.Replace('Opaque', 'invalid') }
                if ($scenario -in @('check-present', 'create-present') -or
                    ($state.Creates -eq 1 -and $scenario -ne 'postcheck-failure')) { return $validJson }
                return ''
            }
            if ($Arguments[0] -eq 'create') {
                $state.Creates++
                Assert-Fixture (($Arguments -join ' ') -ceq 'create -f - --output=name')
                Assert-Fixture (-not $ReadOutput)
                $sent = ConvertFrom-Json $InputJson -AsHashtable
                Assert-RestSecretContract (Get-ManifestContract $sent)
                Assert-Fixture ($sent.data['consumer-key'] -ceq $fixtureData['consumer-key'])
                Assert-Fixture ($sent.data['consumer-secret'] -ceq $fixtureData['consumer-secret'])
                if ($scenario -eq 'create-failure') { throw 'TEST-ONLY create failure or name race' }
                return
            }
            throw 'Unapproved fake operation'
        }
        $fakeRead = {
            param($KeyName)
            $state.Prompts.Add($KeyName)
            if ($scenario -eq 'invalid-first-input' -or
                ($scenario -eq 'invalid-second-input' -and $KeyName -eq 'consumer-secret')) {
                return ConvertTo-SecretData ''
            }
            return $fixtureData[$KeyName]
        }
        $action = if ($scenario.StartsWith('check-')) { 'Check' } else { 'Create' }
        $failed = $false
        $result = ''
        try { $result = Invoke-RestSecretPreparation $action $fakeRun $fakeRead }
        catch { $failed = $true }
        Assert-Fixture ($failed -eq ($scenario -in @('conflict', 'read-failure', 'create-failure',
            'postcheck-failure', 'no-context', 'no-namespace', 'invalid-first-input', 'invalid-second-input')))
        $writes = if ($scenario -in @('create-missing', 'create-failure', 'postcheck-failure')) { 1 } else { 0 }
        Assert-Fixture ($state.Creates -eq $writes)
        $prompts = switch ($scenario) {
            'invalid-first-input' { 1 }
            'invalid-second-input' { 2 }
            default { 2 * $writes }
        }
        Assert-Fixture ($state.Prompts.Count -eq $prompts)
        if ($writes -eq 1) {
            Assert-Fixture (($state.Prompts -join ',') -ceq 'consumer-key,consumer-secret')
        }
        if ($scenario -eq 'check-missing') { Assert-Fixture ($result.StartsWith('absent;')) }
        if ($scenario -eq 'create-missing') { Assert-Fixture ($result.StartsWith('created;')) }
        if ($scenario -in @('check-present', 'create-present')) { Assert-Fixture ($result.Contains('preserved')) }
    }
    $script:Operation = 'offline validation'
    Write-Host ('Offline validation passed: ' + $script:Assertions + ' assertions; parser, manifest and workflow fixtures.')
    Write-Host 'No kubectl, interactive prompt, credential files, generated keys or cluster access used.'
}

try {
    Write-Host 'Target: k3d-urumi-local / urumi / urumi-woocommerce-rest'
    if ($Mode -eq 'Validate') { Invoke-OfflineValidation }
    else {
        $script:Operation = 'locating kubectl'
        $script:KubectlPath = (Get-Command kubectl -CommandType Application -ErrorAction Stop).Source
        $runner = {
            param([string[]] $Arguments, [string] $InputJson = '', [switch] $ReadOutput)
            Invoke-RestKubectl -Arguments $Arguments -InputJson $InputJson -ReadOutput:$ReadOutput
        }
        $reader = { param($KeyName) Read-EncodedCredential $KeyName }
        $status = Invoke-RestSecretPreparation -Action $Mode -RunKubectl $runner -ReadCredential $reader
        Write-Host ('urumi-woocommerce-rest: ' + $status)
    }
}
catch {
    # Never forward $_, Exception.Message, child output, parsing errors or input values.
    [Console]::Error.WriteLine('WooCommerce REST Secret preparation failed during ' + $script:Operation +
        '. No replace, patch, delete or retry was attempted. Inspect state before retrying.')
    exit 1
}
