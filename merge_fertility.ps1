# PowerShell script to merge fertility into planet resources CSV
Write-Host "Merging fertility data into planet resources..."

# Load CSVs
$planetRes = Import-Csv "pu-tracker\cache\planetresources.csv"
$fertility = Import-Csv "pu-tracker\cache\planet_fertility.csv"

Write-Host "Loaded $($planetRes.Count) planet resources"
Write-Host "Loaded $($fertility.Count) planets with fertility"

# Create hash table for quick lookup
$fertilityHash = @{}
foreach ($row in $fertility) {
    $fertilityHash[$row.Planet] = $row.Fertility
}

# Add Fertility column to each row
$result = @()
foreach ($row in $planetRes) {
    $newRow = [PSCustomObject]@{
        Key = $row.Key
        Planet = $row.Planet
        Ticker = $row.Ticker
        Type = $row.Type
        Factor = $row.Factor
        Fertility = $fertilityHash[$row.Planet]
    }
    $result += $newRow
}

# Export merged CSV
$outputPath = "pu-tracker\cache\planetresources_with_fertility.csv"
$result | Export-Csv $outputPath -NoTypeInformation

Write-Host "✓ Created $outputPath with Fertility column"
Write-Host ""
Write-Host "Sample rows with fertility:"
$result | Where-Object { $_.Fertility } | Select-Object -First 5 | Format-Table

Write-Host ""
Write-Host "Now upload this file to Google Sheets Planet Resources tab"
Write-Host "Or wait for the GitHub Actions pipeline to run automatically"
