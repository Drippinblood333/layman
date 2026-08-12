$ErrorActionPreference = 'Stop'
$command = Get-Command layman -ErrorAction Stop
& $command.Source start
