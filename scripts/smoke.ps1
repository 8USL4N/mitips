param(
  [string]$BackendUrl = "http://localhost:8000",
  [string]$FrontendUrl = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Step {
  param([string]$Message)
  Write-Host "[SMOKE] $Message"
}

Step "Проверка backend root"
$rootResponse = Invoke-RestMethod -Uri "$BackendUrl/"
Assert-True ($rootResponse.status -eq "ok") "Backend root не вернул status=ok"

Step "Проверка backend docs"
$docsStatus = (Invoke-WebRequest -UseBasicParsing -Uri "$BackendUrl/docs").StatusCode
Assert-True ($docsStatus -eq 200) "Backend /docs недоступен"

Step "Проверка frontend"
$frontendStatus = (Invoke-WebRequest -UseBasicParsing -Uri "$FrontendUrl/").StatusCode
Assert-True ($frontendStatus -eq 200) "Frontend недоступен"

Step "Проверка списка диагнозов"
$diagnoses = Invoke-RestMethod -Uri "$BackendUrl/api/diagnoses"
$diagnosisCount = @($diagnoses).Count
Assert-True ($diagnosisCount -ge 9) "Ожидалось минимум 9 диагнозов, получено: $diagnosisCount"

$targetDiagnosis = $diagnoses | Where-Object { $_.icd10 -eq "A00" } | Select-Object -First 1
Assert-True ($null -ne $targetDiagnosis) "Не найден диагноз с icd10=A00"

$details = Invoke-RestMethod -Uri "$BackendUrl/api/diagnoses/$($targetDiagnosis.id)"
$values = @{}

foreach ($criterion in $details.criteria) {
  $charId = [string]$criterion.characteristic_id
  if ($criterion.characteristic_type -eq "range") {
    $values[$charId] = [math]::Round((($criterion.expected_min + $criterion.expected_max) / 2), 1)
  }
  else {
    $values[$charId] = "$($criterion.expected_enum_key)"
  }
}

$solvePayload = @{
  diagnosis_id = $targetDiagnosis.id
  patient_values = $values
}

Step "Проверка solve"
$solveBody = [System.Text.Encoding]::UTF8.GetBytes(($solvePayload | ConvertTo-Json -Depth 8))
$solveResponse = Invoke-RestMethod -Method Post -Uri "$BackendUrl/api/solver/solve" -ContentType "application/json; charset=utf-8" -Body $solveBody
Assert-True ($solveResponse.icd10 -eq "A00") "Solve вернул неожидаемый диагноз (icd10)"
Assert-True ($solveResponse.matched_count -eq $solveResponse.total_count) "Для эталонных симптомов ожидалось полное совпадение"

$treatments = Invoke-RestMethod -Uri "$BackendUrl/api/treatments"
$treatment = $treatments | Where-Object { $_.id -eq $targetDiagnosis.treatment_id } | Select-Object -First 1
Assert-True ($null -ne $treatment) "Не найдено лечение выбранного диагноза"

$originalActions = @($treatment.actions)
$tempStep = "SMOKE_STEP_" + [guid]::NewGuid().ToString("N")

try {
  Step "Проверка сценария: изменили БД -> изменение видно в решателе"
  $updatedActions = @($originalActions + $tempStep)
  $updatePayload = [System.Text.Encoding]::UTF8.GetBytes((@{ actions = $updatedActions } | ConvertTo-Json -Depth 8))

  Invoke-RestMethod -Method Put -Uri "$BackendUrl/api/treatments/$($treatment.id)/actions" -ContentType "application/json; charset=utf-8" -Body $updatePayload | Out-Null

  $solveAfterUpdate = Invoke-RestMethod -Method Post -Uri "$BackendUrl/api/solver/solve" -ContentType "application/json; charset=utf-8" -Body $solveBody
  Assert-True (($solveAfterUpdate.actions -contains $tempStep)) "Новый шаг лечения не появился в ответе решателя"
}
finally {
  Step "Откат временного изменения лечения"
  $rollbackPayload = [System.Text.Encoding]::UTF8.GetBytes((@{ actions = $originalActions } | ConvertTo-Json -Depth 8))
  Invoke-RestMethod -Method Put -Uri "$BackendUrl/api/treatments/$($treatment.id)/actions" -ContentType "application/json; charset=utf-8" -Body $rollbackPayload | Out-Null
}

Step "Все smoke-проверки пройдены"
Write-Host 'SMOKE RESULT: PASS'
