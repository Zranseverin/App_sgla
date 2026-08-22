$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$audioDirectory = Join-Path $projectRoot 'apps\entreprises\static\entreprises\media\video'
$voicePath = Join-Path $audioDirectory 'cleango-voix-feminine.wav'

$narration = @"
Votre voiture est sale, et vous ne savez pas où aller ? Découvrez CleanGo. Depuis votre téléphone, localisez les stations de lavage les plus proches. Consultez leurs catalogues, leurs services et leurs prix, puis choisissez votre lavage. CleanGo vous indique l'itinéraire jusqu'à la station. À votre arrivée, la caissière enregistre votre nom et votre véhicule. Pendant que les professionnels prennent soin de votre voiture, détendez-vous. Payez simplement avec Wave, puis repartez satisfait. CleanGo, l'idée du lavage en un clic. Retrouvez-nous sur www point cleango point ci.
"@

$speaker = New-Object -ComObject SAPI.SpVoice
$femaleVoice = $speaker.GetVoices() | Where-Object { $_.GetDescription() -like '*Hortense*' } | Select-Object -First 1
if (-not $femaleVoice) {
    throw 'La voix française féminine Microsoft Hortense est introuvable.'
}
$speaker.Voice = $femaleVoice
$speaker.Rate = 2
$speaker.Volume = 100

$stream = New-Object -ComObject SAPI.SpFileStream
$stream.Format.Type = 22
$stream.Open($voicePath, 3, $false)
$speaker.AudioOutputStream = $stream
[void]$speaker.Speak($narration)
$stream.Close()

Write-Output "Voix créée : $voicePath"
