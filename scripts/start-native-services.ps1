param(
    [string]$ServiceRoot = 'C:\Users\linth\Documents\Codex\2026-09-19\files-mentioned-by-the-user-csc357\work\services'
)

$ErrorActionPreference = 'Stop'

function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync('127.0.0.1', $Port)
        return $connection.Wait(1000) -and $client.Connected
    } catch { return $false }
    finally { $client.Dispose() }
}

function Wait-LocalPort([int]$Port, [System.Diagnostics.Process]$Process) {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-LocalPort $Port) { return }
        if ($Process.HasExited) { throw "Service exited. Check logs in $ServiceRoot." }
        Start-Sleep -Seconds 1
    }
    throw "Service did not become available on port $Port. Check logs in $ServiceRoot."
}

# Use the existing project database; never initialize or replace its data directory.
if (!(Test-LocalPort 3307)) {
    $mysqlBase = Join-Path $ServiceRoot 'mysql\mysql-8.4.11-winx64'
    $mysqlData = Join-Path $ServiceRoot 'mysql-data'
    $mysqlExecutable = Join-Path $mysqlBase 'bin\mysqld.exe'
    if (!(Test-Path -LiteralPath $mysqlExecutable) -or !(Test-Path -LiteralPath (Join-Path $mysqlData 'auto.cnf'))) {
        throw 'Existing standalone MySQL installation/data not found. Pass the correct -ServiceRoot.'
    }
    $mysqlArguments = @(
        '--no-defaults', ('--basedir="{0}"' -f $mysqlBase),
        ('--datadir="{0}"' -f $mysqlData), '--port=3307',
        '--bind-address=127.0.0.1', '--mysqlx=OFF', '--console'
    )
    $mysqlProcess = Start-Process -FilePath $mysqlExecutable -ArgumentList $mysqlArguments `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $ServiceRoot 'mysql-native.stdout.log') `
        -RedirectStandardError (Join-Path $ServiceRoot 'mysql-native.stderr.log')
    Wait-LocalPort 3307 $mysqlProcess
}

if (!(Test-LocalPort 1025)) {
    $mailpitExecutable = Join-Path $ServiceRoot 'mailpit\mailpit.exe'
    if (!(Test-Path -LiteralPath $mailpitExecutable)) { throw 'Mailpit not found in ServiceRoot.' }
    $mailpitArguments = @(
        '--listen', '127.0.0.1:8025', '--smtp', '127.0.0.1:1025',
        '--database', ('"{0}"' -f (Join-Path $ServiceRoot 'mailpit.db'))
    )
    $mailpitProcess = Start-Process -FilePath $mailpitExecutable -ArgumentList $mailpitArguments `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $ServiceRoot 'mailpit-native.stdout.log') `
        -RedirectStandardError (Join-Path $ServiceRoot 'mailpit-native.stderr.log')
    Wait-LocalPort 1025 $mailpitProcess
}

Write-Host 'Local services available: MySQL on 127.0.0.1:3307; Mailpit at http://127.0.0.1:8025.'
Write-Host 'Start FastAPI and Next.js using the normal development commands. Docker is not required.'
